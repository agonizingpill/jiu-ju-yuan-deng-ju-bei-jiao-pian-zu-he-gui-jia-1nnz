        import {workspace} from '../workspace.js';
        import {el} from '../dom.js';

        const page = {
  "title": "透过率采样和复测",
  "module": "可见波段扫描",
  "caption": "可见波段扫描",
  "detail": "光台记录从 450 nm 到 650 nm 的四个区间均值，保留一次原始扫描凭单。",
  "path": "/gel_curves",
  "columns": [
    {
      "name": "code",
      "label": "编号"
    },
    {
      "name": "reel",
      "label": "胶片卷"
    },
    {
      "name": "bands",
      "label": "四波段透过率"
    },
    {
      "name": "rechecked",
      "label": "已复测"
    }
  ],
  "layout": "stack",
  "view": "table",
  "actions": [
    {
      "name": "scan_gel",
      "label": "记录四波段扫描",
      "path": "/gel_curves/scan-gel",
      "fields": [
        {
          "name": "code",
          "label": "扫描号",
          "kind": "text",
          "initial": "SP-RUBY"
        },
        {
          "name": "reel",
          "label": "色片卷",
          "kind": "text",
          "initial": "REEL-H"
        },
        {
          "name": "bands",
          "label": "四波段透过率",
          "kind": "json",
          "initial": [
            0.8,
            0.49,
            0.24,
            0.14
          ]
        }
      ],
      "help": "保持固定波段顺序。",
      "roles": [
        "operator",
        "reviewer"
      ],
      "success": "已写入"
    },
    {
      "name": "recheck_curve",
      "label": "签认光台复测",
      "path": "/gel_curves/recheck-curve",
      "fields": [
        {
          "name": "curve",
          "label": "曲线号",
          "kind": "text",
          "initial": "SP-RUBY"
        }
      ],
      "help": "重新对比滤镜卡位。",
      "roles": [
        "reviewer"
      ],
      "success": "已写入"
    }
  ]
};

        export const {title} = page;
        export const key = "gel_curves";
        export async function render(root, role) {
          await workspace(root, role, page);

        }
