import type { editor } from "monaco-editor";
export const editorThemes: Record<string, editor.IStandaloneThemeData> = {
  "samyak-light": {
    base: "vs",
    inherit: true,
    rules: [
      { token: "keyword", foreground: "8D6233", fontStyle: "bold" },
      { token: "string", foreground: "2B7350" },
      { token: "comment", foreground: "7B7973", fontStyle: "italic" },
      { token: "number", foreground: "A0561A" },
    ],
    colors: {
      "editor.background": "#FFFFFF",
      "editor.foreground": "#1F2123",
      "editorLineNumber.foreground": "#ABA79E",
      "editorLineNumber.activeForeground": "#896235",
      "editor.selectionBackground": "#E8D9C1",
      "editor.lineHighlightBackground": "#F5F5F3",
      "editorCursor.foreground": "#956D39",
      "editorGutter.background": "#FFFFFF",
      "editorWidget.background": "#F5F5F3",
      "editorWidget.border": "#E4E2DD",
    },
  },
  "samyak-dark": {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "keyword", foreground: "CFAC74", fontStyle: "bold" },
      { token: "string", foreground: "8FC5A6" },
      { token: "comment", foreground: "84817B", fontStyle: "italic" },
      { token: "number", foreground: "D7AB7C" },
    ],
    colors: {
      "editor.background": "#15171A",
      "editor.foreground": "#ECE9E3",
      "editorLineNumber.foreground": "#625F59",
      "editorLineNumber.activeForeground": "#CFAC74",
      "editor.selectionBackground": "#4C4030",
      "editor.lineHighlightBackground": "#1D1F22",
      "editorCursor.foreground": "#CFAC74",
      "editorGutter.background": "#15171A",
      "editorWidget.background": "#1D1F22",
      "editorWidget.border": "#343332",
    },
  },
};
