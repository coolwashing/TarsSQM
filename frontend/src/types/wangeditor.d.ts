/**
 * WangEditor 5 模块类型补充声明
 * 解决 TS 在 bundler 模式下对 @wangeditor/editor-for-vue exports 的解析限制
 */
declare module '@wangeditor/editor-for-vue' {
  import type { DefineComponent } from 'vue'
  export const Editor: DefineComponent<any, any, any>
  export const Toolbar: DefineComponent<any, any, any>
}
