import {awaitCompute, request} from '../api.js';
import {el, display} from '../dom.js';
import {COMPUTE_STATES, evidence} from '../store.js';
import {status, titleBlock} from '../widgets.js';

const title = '统一成分基准与换版';
const key = 'nmf_baselines';

const STATUS_LABEL = {active: '在用', staged: '待切换', retired: '已退役'};

function baselineCards(rows) {
  if (!rows.length) return status('尚无基准记录。');
  return el('div', {class: 'records grid'}, rows.map(row =>
    el('article', {class: 'record'},
      el('h3', {}, row.code),
      el('dl', {},
        el('dt', {}, '状态'), el('dd', {}, STATUS_LABEL[row.status] || row.status),
        el('dt', {}, '复测样本'), el('dd', {}, display(row.references)),
        el('dt', {}, '基准重构均误'), el('dd', {}, display(row.mean_error)),
        el('dt', {}, '计算凭据'), el('dd', {}, display(row.token))))));
}

function conversionPanel(summary) {
  if (!summary.staged) return status('当前没有待切换基准，归盒与调出均按在用基准进行。');
  const items = [
    ['待切换基准', summary.staged],
    ['在盒签条', summary.in_box.join(' · ') || '—'],
    ['已换算', summary.ready.join(' · ') || '—'],
    ['待结算', summary.pending.join(' · ') || '—'],
    ['换算失败', summary.failed.join(' · ') || '—'],
  ];
  return el('article', {class: 'record'},
    el('h3', {}, '换版对账'),
    el('dl', {}, ...items.flatMap(([k, v]) => [el('dt', {}, k), el('dd', {}, v)])),
    status(summary.matched ? '新谱与在盒签条已全部对上，可一次性切换。'
      : '仍有签条未完成换算，切换保持锁定。', summary.matched ? 'ok' : 'error'));
}

// 表单定义：token 字段不写 initial，自动带出最近一次计算凭据。
const FORMS = [
  {
    id: 'build-baseline', label: '用复测曲线建新基准', buttonLabel: '拟合新基准',
    help: '拟合一条待切换基准；建立期间归盒与调出仍按旧的在用基准进行。',
    fields: [{name: 'note', label: '说明（可选）', initial: ''}],
  },
  {
    id: 'save-baseline', label: '签存待切换基准', buttonLabel: '登记基准',
    help: '凭拟合任务号登记为待切换基准，不影响在用基准。',
    fields: [{name: 'code', label: '基准编号', initial: 'NMF-BASE-02'},
      {name: 'token', label: '拟合凭据'}],
  },
  {
    id: 'convert-profile', label: '换算在盒签条', buttonLabel: '发起换算',
    help: '把签条投影到待切换基准；排队中重试不重复启用，失败或凭据过期则用原曲线重算。',
    fields: [{name: 'baseline', label: '待切换基准', initial: 'NMF-BASE-02'},
      {name: 'profile', label: '在盒签条', initial: 'NMF-0'}],
  },
  {
    id: 'settle-conversion', label: '结算换算结果', buttonLabel: '结算',
    help: '成功写入新权重；失败则保留旧基准找片，可稍后用原曲线重试。',
    fields: [{name: 'baseline', label: '待切换基准', initial: 'NMF-BASE-02'},
      {name: 'profile', label: '签条', initial: 'NMF-0'},
      {name: 'token', label: '换算凭据'}],
  },
  {
    id: 'activate-baseline', label: '一次性切换在用基准', buttonLabel: '切换基准',
    help: '仅当在盒签条全部换算成功时可用，切换后整体改用新基准。',
    fields: [{name: 'baseline', label: '待切换基准', initial: 'NMF-BASE-02'}],
  },
];

function formBox(spec, role, onDone) {
  const notice = status('');
  const form = el('form', {class: 'action', id: spec.id},
    el('h3', {}, spec.label), el('p', {}, spec.help),
    el('div', {class: 'fields'}, spec.fields.map(field => el('label', {},
      el('span', {}, field.label),
      el('input', {name: field.name, type: 'text',
        value: field.initial ?? evidence.get(), required: ''})))),
    el('button', {type: 'submit'}, spec.buttonLabel), notice);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    notice.className = 'status';
    try {
      const payload = await request('/nmf_baselines/' + spec.id,
        Object.fromEntries(new FormData(form)));
      if (payload.token) evidence.save(payload.token);
      if (payload.token && payload.status === 'queued') {
        const result = await awaitCompute(payload.token, current => {
          notice.textContent = COMPUTE_STATES[current.status] || current.status;
        });
        if (result.status === 'rejected') throw new Error(result.detail);
        notice.textContent = '任务 ' + payload.token + ' · ' + display(result.result);
      } else {
        notice.textContent = display(payload);
      }
      notice.className = 'status ok';
      await onDone();
    } catch (error) {
      notice.className = 'status error';
      notice.textContent = error.message;
    }
  });
  return form;
}

export async function render(root, role) {
  const ledger = el('section', {class: 'ledger', 'aria-label': '统一基准'});
  const conversion = el('section', {class: 'ledger', 'aria-label': '换版对账'});

  const refresh = async () => {
    const [rows, summary] = await Promise.all([
      request('/nmf_baselines'), request('/nmf_baselines/conversions')]);
    ledger.replaceChildren(el('h2', {}, '基准台账'), baselineCards(rows));
    conversion.replaceChildren(el('h2', {}, '在盒签条换算对账'), conversionPanel(summary));
  };

  const forms = role === 'reviewer'
    ? FORMS.map(spec => formBox(spec, role, refresh))
    : [status('仅复核员可建立基准、换算签条与切换；当前角色只读。')];

  root.replaceChildren(
    titleBlock('统一成分基准', title,
      '全部签条与找片共用同一套 NMF 基准；复核员用复测曲线建新基准，等在盒签条全对上后一次性切换。'),
    el('div', {class: 'work stack'}, ledger, conversion,
      el('section', {class: 'actions'}, ...forms)));
  await refresh();
}
