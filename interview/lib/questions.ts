import type { Section } from "./types";

export const SECTIONS: Section[] = [
  {
    id: "background",
    title: "Background & Role",
    titleKo: "배경 및 역할",
    duration: "~10 min",
    intro:
      "First, a quick check on your role and how much exposure you've already had to the Korean immigration system.",
    introKo:
      "먼저 챗봇 프로젝트에서의 역할과, 한국 출입국/비자 시스템에 대한 사전 노출 정도를 가볍게 확인하는 섹션입니다.",
    questions: [
      {
        id: "q1_role",
        number: "Q1",
        type: "multi",
        prompt:
          "What is your role on the chatbot project? (Select all that apply)",
        promptKo:
          "챗봇 프로젝트에서 맡은 역할은 무엇인가요? (해당되는 항목을 모두 선택)",
        options: [
          { value: "frontend", label: "Frontend", labelKo: "프론트엔드" },
          { value: "backend", label: "Backend", labelKo: "백엔드" },
          {
            value: "llm",
            label: "LLM / model integration",
            labelKo: "LLM / 모델 연동",
          },
          {
            value: "data",
            label: "Data / retrieval",
            labelKo: "데이터 / 검색",
          },
          { value: "pm", label: "Product / PM", labelKo: "기획 / PM" },
          { value: "all", label: "All of the above", labelKo: "전부" },
        ],
      },
      {
        id: "q2_stage",
        number: "Q2",
        type: "long",
        prompt:
          "How long have you been working on this, and what stage is the chatbot currently in?",
        promptKo:
          "이 프로젝트를 얼마나 진행했으며, 챗봇은 현재 어느 단계에 있나요?",
        placeholder:
          "e.g. Started 6 weeks ago. We have a working prototype that answers a small set of D-2 questions, but routing and evaluation are still rough.",
      },
      {
        id: "q3_familiarity",
        number: "Q3",
        type: "single",
        prompt:
          "Before joining, how familiar were you with the Korean immigration and visa system?",
        promptKo:
          "이 프로젝트에 참여하기 전, 한국 출입국·비자 시스템에 대해 얼마나 알고 있었나요?",
        options: [
          {
            value: "none",
            label: "Not familiar at all",
            labelKo: "전혀 모름",
          },
          {
            value: "personal",
            label: "Only from personal experience (my own visa)",
            labelKo: "본인 비자 등 개인 경험 정도",
          },
          {
            value: "some",
            label: "Some — I've researched it a bit",
            labelKo: "어느 정도 — 직접 조사해본 경험 있음",
          },
          {
            value: "deep",
            label: "Deep — I've worked on related projects before",
            labelKo: "잘 알고 있음 — 관련 프로젝트 경험 있음",
          },
        ],
      },
      {
        id: "q4_manual_read",
        number: "Q4",
        type: "single",
        prompt:
          "Have you read any part of the Korean immigration manual (체류민원 or 사증민원)?",
        promptKo:
          "한국 출입국 매뉴얼 (체류민원 또는 사증민원)을 읽어본 적 있나요?",
        options: [
          { value: "no", label: "No", labelKo: "아니오" },
          {
            value: "skimmed",
            label: "Skimmed parts of it",
            labelKo: "일부 훑어봄",
          },
          {
            value: "specific",
            label: "Read specific sections for a task",
            labelKo: "특정 업무 때문에 특정 섹션을 정독함",
          },
          {
            value: "thorough",
            label: "Read most of it thoroughly",
            labelKo: "대부분 정독함",
          },
        ],
      },
    ],
  },
  {
    id: "architecture",
    title: "Chatbot Architecture",
    titleKo: "챗봇 아키텍처",
    duration: "~15 min",
    intro:
      "Now the technical core — how a user query becomes an answer in your current build.",
    introKo:
      "기술적인 코어 — 사용자의 질문이 현재 챗봇에서 답변으로 변환되는 과정을 짚는 섹션입니다.",
    questions: [
      {
        id: "q5_architecture",
        number: "Q5",
        type: "long",
        prompt:
          "Walk us through your current chatbot architecture. How does a user query flow from input to answer?",
        promptKo:
          "현재 챗봇 아키텍처를 설명해 주세요. 사용자 질문이 입력부터 답변까지 어떻게 흐르나요?",
        placeholder:
          "Input → preprocessing → routing → retrieval → LLM → post-processing → response. Mention key components, services, and any notable trade-offs.",
      },
      {
        id: "q6_retrieval",
        number: "Q6",
        type: "multi",
        prompt:
          "What retrieval method(s) are you currently using? (Select all that apply)",
        promptKo:
          "어떤 검색 방식을 사용하고 있나요? (해당되는 항목을 모두 선택)",
        options: [
          {
            value: "keyword",
            label: "Keyword / lexical search",
            labelKo: "키워드 검색",
          },
          {
            value: "vector",
            label: "Vector search / RAG",
            labelKo: "벡터 검색 / RAG",
          },
          {
            value: "hybrid",
            label: "Hybrid (keyword + vector)",
            labelKo: "하이브리드 (키워드 + 벡터)",
          },
          {
            value: "finetune",
            label: "Fine-tuned model",
            labelKo: "파인튜닝 모델",
          },
          {
            value: "rules",
            label: "Rule-based routing",
            labelKo: "규칙 기반 라우팅",
          },
          { value: "none", label: "None yet", labelKo: "아직 없음" },
        ],
      },
      {
        id: "q7_data_source",
        number: "Q7",
        type: "multi",
        prompt:
          "What data source is the chatbot currently using? (Select all that apply)",
        promptKo:
          "챗봇이 현재 사용하는 데이터 소스는 무엇인가요? (해당되는 항목을 모두 선택)",
        options: [
          { value: "raw_pdf", label: "Raw PDF / HWP", labelKo: "원본 PDF / HWP" },
          {
            value: "manual_qa",
            label: "Manually written Q&A",
            labelKo: "수동 작성 Q&A",
          },
          {
            value: "existing_csv",
            label: "An existing structured CSV",
            labelKo: "기존 구조화된 CSV",
          },
          {
            value: "web",
            label: "Scraped web pages (HiKorea, embassy sites)",
            labelKo: "웹 스크래핑 (하이코리아, 대사관 등)",
          },
          { value: "none", label: "None yet", labelKo: "아직 없음" },
        ],
      },
      {
        id: "q8_user_language",
        number: "Q8",
        type: "long",
        prompt:
          "Users don't know visa codes like E-7 or F-6 — they just describe their situation. How are you handling that gap today?",
        promptKo:
          "사용자가 E-7이나 F-6 같은 비자 코드를 모르고 자신의 상황만 설명하는 경우를 어떻게 처리하고 있나요?",
        placeholder:
          "e.g. We currently rely on the LLM to infer the code from free text — but accuracy is mixed.",
      },
      {
        id: "q9_routing",
        number: "Q9",
        type: "long",
        prompt:
          "Do you have a routing or intent classification layer before retrieval? If so, how is it built?",
        promptKo:
          "검색 전에 라우팅 또는 인텐트 분류 단계가 있나요? 있다면 어떻게 구성했나요?",
        placeholder:
          "Optional — describe the classifier (LLM prompt, lightweight model, keyword rules) and which buckets you route into.",
        optional: true,
      },
      {
        id: "q10_model",
        number: "Q10",
        type: "long",
        prompt:
          "What LLM/model are you using for response generation? How are you managing context length and hallucination risk?",
        promptKo:
          "응답 생성에 어떤 LLM 또는 모델을 사용하고 있나요? 컨텍스트 길이와 환각(hallucination) 위험은 어떻게 관리하고 있나요?",
        placeholder:
          "Model name, provider, system prompt strategy, citation/grounding approach, evaluation method.",
      },
      {
        id: "q10a_chunking",
        number: "Q10-a",
        type: "long",
        prompt: "(If using RAG) What is your chunking strategy?",
        promptKo: "(RAG 사용 시) 청킹(chunking) 전략은 무엇인가요?",
        help: "Only fill in if you answered RAG / vector / hybrid in Q6.",
        helpKo: "Q6에서 RAG/벡터/하이브리드를 선택한 경우에만 답변해 주세요.",
        optional: true,
        dependsOn: {
          questionId: "q6_retrieval",
          values: ["vector", "hybrid"],
        },
      },
      {
        id: "q10b_embedding",
        number: "Q10-b",
        type: "short",
        prompt: "(If using RAG) What embedding model are you using?",
        promptKo: "(RAG 사용 시) 어떤 임베딩 모델을 사용하고 있나요?",
        placeholder: "e.g. text-embedding-3-large, bge-m3, multilingual-e5...",
        optional: true,
        dependsOn: {
          questionId: "q6_retrieval",
          values: ["vector", "hybrid"],
        },
      },
      {
        id: "q10c_multihop",
        number: "Q10-c",
        type: "long",
        prompt:
          '(If using RAG) How do you handle multi-hop questions (e.g., "I want to change my D-2 to E-7 and also bring my spouse")?',
        promptKo:
          '(RAG 사용 시) 여러 단계에 걸친 복합 질문은 어떻게 처리하나요? (예: "D-2를 E-7로 변경하고 배우자도 데려오고 싶어요")',
        optional: true,
        dependsOn: {
          questionId: "q6_retrieval",
          values: ["vector", "hybrid"],
        },
      },
    ],
  },
  {
    id: "data_briefing",
    title: "Data Briefing",
    titleKo: "데이터 브리핑",
    duration: "~15 min",
    intro:
      "Before the next questions, please read the data briefing on the side. It summarizes what our preprocessing pipeline produced and how it is meant to be consumed.",
    introKo:
      "다음 질문 전에 옆의 데이터 브리핑을 먼저 읽어주세요. 우리 전처리 파이프라인이 만든 결과물과, 그것을 어떻게 쓰면 좋을지를 정리해 두었습니다.",
    questions: [
      {
        id: "briefing_read",
        number: "Read",
        type: "single",
        prompt: "I have read the data briefing on the right side.",
        promptKo: "우측의 데이터 브리핑을 읽었습니다.",
        options: [
          {
            value: "yes",
            label: "Yes, I've read it",
            labelKo: "네, 읽었습니다",
          },
        ],
      },
    ],
  },
  {
    id: "gap",
    title: "Gap Analysis & Integration",
    titleKo: "격차 파악 및 통합",
    duration: "~10 min",
    intro:
      "Now that you've seen what the CSVs contain, let's see how they fit your build.",
    introKo:
      "CSV 내용을 확인했으니, 현재 챗봇 빌드에 어떻게 들어맞는지를 확인하는 섹션입니다.",
    questions: [
      {
        id: "q11_useful_fields",
        number: "Q11",
        type: "long",
        prompt:
          "Which fields look most immediately useful for your current chatbot design?",
        promptKo:
          "현재 챗봇 설계에 가장 즉각적으로 유용한 필드는 무엇인가요?",
        placeholder:
          "e.g. situation_tags + routing_hint for intent classification; plain_language_summary for the final answer.",
      },
      {
        id: "q12_uncovered_questions",
        number: "Q12",
        type: "long",
        prompt:
          "Are there user questions your chatbot handles today that these CSVs would NOT cover?",
        promptKo:
          "현재 챗봇이 처리하는 사용자 질문 중 이 CSV로는 커버되지 않는 것이 있나요?",
        help: "Examples: HiKorea submission flow, fee payment, appeal process, embassy hours.",
        helpKo:
          "예: 하이코리아 제출 절차, 수수료 납부, 이의신청 절차, 대사관 영업시간 등.",
      },
      {
        id: "q13_missing_fields",
        number: "Q13",
        type: "long",
        prompt:
          "Are there fields missing from the CSV that you need?",
        promptKo: "CSV에 필요한데 빠진 필드가 있나요?",
        help: "Examples: processing time estimates, office locations, embassy contacts.",
        helpKo: "예: 처리 기간 예상, 사무소 위치, 대사관 연락처 등.",
      },
      {
        id: "q14_updates",
        number: "Q14",
        type: "long",
        prompt:
          "How are you planning to handle updates when a new version of the manual is released?",
        promptKo:
          "매뉴얼 새 버전이 출시될 때 업데이트를 어떻게 처리할 계획인가요?",
        optional: true,
      },
      {
        id: "q15_languages",
        number: "Q15",
        type: "long",
        prompt:
          "Are you considering a bilingual (Korean/English) or multilingual chatbot? If so, which fields need translation first?",
        promptKo:
          "한국어/영어 이중 언어 또는 다국어 챗봇을 고려하고 있나요? 그렇다면 어떤 필드를 먼저 번역해야 할까요?",
      },
    ],
  },
  {
    id: "feedback",
    title: "Feedback & Requests",
    titleKo: "피드백 및 요청 사항",
    duration: "~5 min",
    intro:
      "Last stretch — your asks back to the data team.",
    introKo: "마지막 섹션 — 데이터팀에 요청하고 싶은 사항을 받습니다.",
    questions: [
      {
        id: "q16_easiest_format",
        number: "Q16",
        type: "long",
        prompt:
          "What would make the CSV data easiest for your pipeline to consume? (format changes, additional columns, pre-built embeddings, etc.)",
        promptKo:
          "파이프라인에서 CSV 데이터를 가장 쉽게 활용하려면 어떻게 하면 좋을까요? (형식 변경, 추가 컬럼, 사전 구성 임베딩 등)",
      },
      {
        id: "q17_walkthrough",
        number: "Q17",
        type: "long",
        prompt:
          "Is there any part of the pipeline or the data you'd like a walkthrough of in a follow-up session?",
        promptKo:
          "후속 세션에서 파이프라인이나 데이터의 어떤 부분을 더 자세히 설명해 드릴까요?",
        optional: true,
      },
      {
        id: "q18_blocker",
        number: "Q18",
        type: "long",
        prompt: "What is your most pressing blocker right now?",
        promptKo: "지금 가장 시급한 막힌 부분은 무엇인가요?",
      },
    ],
  },
];

export const ALL_QUESTIONS = SECTIONS.flatMap((s) => s.questions);
