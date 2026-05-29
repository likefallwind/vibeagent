export type ChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

export interface ChatClient {
  complete(messages: ChatMessage[]): Promise<string>;
}

export type WriteFileAction = {
  type: "write_file";
  path: string;
  content: string;
};

export type RunCommandAction = {
  type: "run_command";
  command: string;
};

export type FinishAction = {
  type: "finish";
  message: string;
};

export type AgentAction = WriteFileAction | RunCommandAction | FinishAction;

export type ModelActionResponse = {
  thought: string;
  action: AgentAction;
};

export type CommandResult = {
  command: string;
  exitCode: number | null;
  stdout: string;
  stderr: string;
  timedOut: boolean;
  signal: NodeJS.Signals | null;
};

export type Observation =
  | {
      kind: "write_file";
      path: string;
      ok: true;
      message: string;
    }
  | {
      kind: "run_command";
      result: CommandResult;
    }
  | {
      kind: "finish";
      message: string;
    };

export type AgentStatus =
  | "thinking"
  | "writing file"
  | "running command"
  | "observed success"
  | "observed failure"
  | "finished";

export type AgentLogger = (status: AgentStatus, detail?: string) => void;
