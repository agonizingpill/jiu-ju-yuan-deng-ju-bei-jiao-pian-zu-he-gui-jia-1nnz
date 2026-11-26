        import {workspace} from '../workspace.js';
        import {el} from '../dom.js';

        const page = {
  "title": "色片卷来源和可测状态",
  "module": "色片卷与批龄",
  "caption": "色片卷与批龄",
  "detail": "不同年份的胶片可共有成分谱参考，但归架按批龄和介质分开。",
  "path": "/gel_reels",
  "columns": [
    {
      "name": "code",
      "label": "编号"
    },
    {
      "name": "family",
      "label": "介质"
    },
    {
      "name": "aged",
      "label": "老化标志"
    },
    {
      "name": "eligible",
      "label": "可上光台"
    }
  ],
  "layout": "flip",
  "view": "stack",
  "actions": [
    {
      "name": "open_light_table",
      "label": "校核介质可上光台",
      "path": "/gel_reels/open-light-table",
      "fields": [
        {
          "name": "reel",
          "label": "色片卷",
          "kind": "text",
          "initial": "REEL-J"
        },
        {
          "name": "eligible",
          "label": "可用",
          "kind": "bool",
          "initial": true
        }
      ],
      "help": "器材保管员根据纸本修理单调整。",
      "roles": [
        "reviewer"
      ],
      "success": "已写入"
    }
  ]
};

        export const {title} = page;
        export const key = "gel_reels";
        export async function render(root, role) {
          await workspace(root, role, page);

        }
