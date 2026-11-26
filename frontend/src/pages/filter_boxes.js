import {request} from '../api.js';
import {el, display} from '../dom.js';
import {actionForm} from '../controls.js';
import {status, dataView, titleBlock} from '../widgets.js';

const title = '胶片盒归架与调出';
const key = 'filter_boxes';

const page = {
  title,
  module: '色片收纳盒',
  caption: '色片收纳盒',
  detail: '同盒色片批龄和介质一致，归架与调出记录维持可用空位；找片时待找色片与在盒签条按同一套在用基准比较。',
  path: '/filter_boxes',
  columns: [
    {name: 'code', label: '编号'},
    {name: 'kind', label: '介质'},
    {name: 'aged', label: '收纳批龄'},
    {name: 'space', label: '空位'},
    {name: 'contents', label: '归架签条'},
  ],
  layout: 'flip',
  view: 'grid',
  actions: [
    {
      name: 'store_profile',
      label: '按批龄归入片盒',
      path: '/filter_boxes/store-profile',
      fields: [
        {name: 'box', label: '收纳盒', kind: 'text', initial: 'BOX-H'},
        {name: 'profile', label: '成分谱签条', kind: 'text', initial: 'NMF-24'},
      ],
      help: '为片盒写入签条并扣减空位。',
      roles: ['operator', 'reviewer'],
      success: '已写入',
    },
    {
      name: 'pull_profile',
      label: '在修理工位调出片盒',
      path: '/filter_boxes/pull-profile',
      fields: [
        {name: 'box', label: '收纳盒', kind: 'text', initial: 'BOX-H'},
        {name: 'profile', label: '调出签条', kind: 'text', initial: 'NMF-24'},
      ],
      help: '调出后释放空位，并保留成分谱。',
      roles: ['reviewer'],
      success: '已写入',
    },
  ],
};

function matchTable(payload) {
  const head = el('thead', {}, el('tr', {},
    ['片盒', '签条', '来源曲线', '在盒权重', '相似度'].map(x => el('th', {scope: 'col'}, x))));
  const rows = payload.matches.length ? payload.matches.map(row =>
    el('tr', {},
      el('td', {}, row.box), el('td', {}, row.profile), el('td', {}, row.curve),
      el('td', {}, display(row.weights)), el('td', {}, display(row.similarity))))
    : [el('tr', {}, el('td', {colspan: '5'}, '在盒签条为空，暂无可比备片。'))];
  return el('div', {class: 'scroll'}, el('table', {}, head, el('tbody', {}, ...rows)));
}

function similarPanel(refresh) {
  const notice = status('');
  const result = el('div', {});
  const form = el('form', {class: 'action', id: 'find_similar'},
    el('h3', {}, '按在用基准找相近备片'),
    el('p', {}, '待找色片与在盒签条都换算到同一套在用基准，再比较成分权重余弦相似度。'),
    el('div', {class: 'fields'}, el('label', {}, el('span', {}, '待找色片曲线号'),
      el('input', {name: 'curve', type: 'text', value: 'SP-RUBY', required: ''}))),
    el('button', {type: 'submit'}, '计算相似度'), notice);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    notice.className = 'status';
    try {
      const payload = await request('/filter_boxes/find-similar',
        Object.fromEntries(new FormData(form)));
      notice.textContent = '在用基准 ' + payload.baseline + ' · 待找权重 ' + display(payload.weights);
      notice.className = 'status ok';
      result.replaceChildren(matchTable(payload));
      await refresh();
    } catch (error) {
      notice.className = 'status error';
      notice.textContent = error.message;
    }
  });
  return el('section', {class: 'ledger', 'aria-label': '同基准相似度'}, form, result);
}

export async function render(root, role) {
  const panel = el('section', {class: 'ledger', 'aria-label': page.caption});
  const refresh = async () => {
    try {
      const rows = await request(page.path);
      panel.replaceChildren(el('h2', {}, page.caption), dataView(rows, page.columns, page.view));
    } catch (error) {
      panel.replaceChildren(status(error.message, 'error'));
    }
  };
  const actionForms = page.actions.filter(x => x.roles.includes(role))
    .map(x => actionForm(x, refresh));
  root.replaceChildren(
    titleBlock(page.module, page.title, page.detail),
    el('div', {class: 'work ' + page.layout},
      panel, similarPanel(refresh),
      actionForms.length ? el('section', {class: 'actions'}, ...actionForms) : null));
  return refresh();
}
