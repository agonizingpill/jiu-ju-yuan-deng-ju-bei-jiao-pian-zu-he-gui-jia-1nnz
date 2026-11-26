        import {workspace} from '../workspace.js';
        import {el} from '../dom.js';

        const page = {
  "title": "色片非负成分谱",
  "module": "成分谱签条",
  "caption": "成分谱签条",
  "detail": "从库内历史透光曲线分解主要成分，展示查询色片的系数和重构差。",
  "path": "/color_profiles",
  "columns": [
    {
      "name": "code",
      "label": "编号"
    },
    {
      "name": "curve",
      "label": "色片曲线"
    },
    {
      "name": "weights",
      "label": "非负成分谱"
    },
    {
      "name": "dominant",
      "label": "主成分编号"
    },
    {
      "name": "error_value",
      "label": "重构均误"
    },
    {
      "name": "token",
      "label": "计算凭据"
    }
  ],
  "layout": "split",
  "view": "grid",
  "actions": [
    {
      "name": "decompose_gel",
      "label": "分解胶片透光成分",
      "path": "/color_profiles/decompose-gel",
      "fields": [
        {
          "name": "curve",
          "label": "曲线号",
          "kind": "text",
          "initial": "SP-RUBY"
        }
      ],
      "help": "已复测历史参与 NMF。",
      "roles": [
        "operator",
        "reviewer"
      ],
      "success": "已写入"
    },
    {
      "name": "save_components",
      "label": "签存色片成分谱",
      "path": "/color_profiles/save-components",
      "fields": [
        {
          "name": "code",
          "label": "成分谱签条号",
          "kind": "text",
          "initial": "NMF-24"
        },
        {
          "name": "token",
          "label": "计算凭据",
          "kind": "token",
          "initial": ""
        }
      ],
      "help": "与原扫描号一起进入归架签条。",
      "roles": [
        "reviewer"
      ],
      "success": "已写入"
    }
  ]
};

        export const {title} = page;
        export const key = "color_profiles";
        export async function render(root, role) {
          await workspace(root, role, page);

        }
