export type QuestionType = "short" | "long" | "single" | "multi";

export interface QuestionOption {
  value: string;
  label: string;
  labelKo?: string;
}

export interface Question {
  id: string;
  number: string;
  type: QuestionType;
  prompt: string;
  promptKo?: string;
  help?: string;
  helpKo?: string;
  placeholder?: string;
  options?: QuestionOption[];
  optional?: boolean;
  /**
   * If set, this question is only shown when the value of `dependsOn.questionId`
   * is one of `dependsOn.values`.
   */
  dependsOn?: { questionId: string; values: string[] };
}

export interface Section {
  id: string;
  title: string;
  titleKo: string;
  duration: string;
  intro?: string;
  introKo?: string;
  questions: Question[];
}

export type Answers = Record<string, string | string[]>;

export interface InterviewSubmission {
  intervieweeName: string;
  intervieweeEmail: string;
  intervieweeRole: string;
  submittedAt: string;
  durationSeconds: number;
  answers: Answers;
}
