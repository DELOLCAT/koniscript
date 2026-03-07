import { ExtensionContext, window } from "vscode";

import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
  Trace,
  TransportKind,
} from "vscode-languageclient/node";

let client: LanguageClient;

export function activate(context: ExtensionContext) {
  // If the extension is launched in debug mode then the debug server options are used
  // Otherwise the run options are used
  const serverOptions: ServerOptions = {
    command: "/home/ahmad/.cargo/bin/uv",
    args: ["run", "server.py"],
    transport: TransportKind.stdio,
    options: {
      cwd: "/home/ahmad/coding/OmniScript/omni_lsp",
    },
  };
  let channel = window.createOutputChannel("OmniScript LSP Trace");
  // Options to control the language client
  const clientOptions: LanguageClientOptions = {
    // Register the server for plain text documents
    documentSelector: [{ scheme: "file", language: "omniscript" }],
    traceOutputChannel: channel,
  };

  // Create the language client and start the client.
  client = new LanguageClient(
    "omniscript",
    "OmniScript LSP",
    serverOptions,
    clientOptions,
  );
  channel.show();

  // Start the client. This will also launch the server
  client.setTrace(Trace.Verbose);
  client.start();
}

export function deactivate() {
  return client?.stop();
}
