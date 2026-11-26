        import {workspace} from '../workspace.js';
        import {el} from '../dom.js';

        const page = {
  "title": "胶片盒归架与调出",
  "module": "色片收纳盒",
  "caption": "色片收纳盒",
  "detail": "同盒色片批龄和介质一致，归架与调出记录维持可用空位。",
  "path": "/filter_boxes",
  "columns": [
    {
      "name": "code",
      "label": "编号"
    },
    {
      "name": "kind",
      "label": "介质"
    },
    {
      "name": "aged",
      "label": "收纳批龄"
    },
    {
      "name": "space",
      "label": "空位"
    },
    {
      "name": "contents",
      "label": "归架签条"
    }
  ],
  "layout": "flip",
  "view": "grid",
  "actions": [
    {
      "name": "store_profile",
      "label": "按批龄归入片盒",
      "path": "/filter_boxes/store-profile",
      "fields": [
        {
          "name": "box",
          "label": "收纳盒",
          "kind": "text",
          "initial": "BOX-H"
        },
        {
          "name": "profile",
          "label": "成分谱签条",
          "kind": "text",
          "initial": "NMF-24"
        }
      ],
      "help": "为片盒写入签条并扣减空位。",
      "roles": [
        "operator",
        "reviewer"
      ],
      "success": "已写入"
    },
    {
      "name": "pull_profile",
      "label": "在修理工位调出片盒",
      "path": "/filter_boxes/pull-profile",
      "fields": [
        {
          "name": "box",
          "label": "收纳盒",
          "kind": "text",
          "initial": "BOX-H"
        },
        {
          "name": "profile",
          "label": "调出签条",
          "kind": "text",
          "initial": "NMF-24"
        }
      ],
      "help": "调出后释放空位，并保留成分谱。",
      "roles": [
        "reviewer"
      ],
      "success": "已写入"
    }
  ]
};

        export const {title} = page;
        export const key = "filter_boxes";
        export async function render(root, role) {
          await workspace(root, role, page);

        }
