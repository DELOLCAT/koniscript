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
    command: "/bin/env",
    args: ['uv', "run", "server.py"],
    transport: TransportKind.stdio,
    options: {
      cwd: "/home/ahmad/coding/koniscript/koni_lsp",
    },
  };
  let channel = window.createOutputChannel("koniscript LSP Trace");
  // Options to control the language client
  const clientOptions: LanguageClientOptions = {
    // Register the server for plain text documents
    documentSelector: [{ scheme: "file", language: "koniscript" }],
    traceOutputChannel: channel,
  };

  // Create the language client and start the client.
  client = new LanguageClient(
    "koniscript",
    "koniscript LSP",
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
