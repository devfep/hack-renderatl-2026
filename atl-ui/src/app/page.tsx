"use client";

import {
  CopilotChatConfigurationProvider,
  CopilotSidebar,
  CopilotThreadsDrawer,
  useConfigureSuggestions,
} from "@copilotkit/react-core/v2";
import React from "react";

import { ResultPanel } from "@/components/result-panel";

import styles from "./page.module.css";

// The agent key registered in the runtime route (`agents: { default: ... }`).
const AGENT_ID = "default";

export default function AtlTransitPage() {
  useConfigureSuggestions({
    suggestions: [
      {
        title: "Least served",
        message:
          "Which Atlanta Communities of Concern get the least weekday bus service?",
      },
      {
        title: "Test the premise",
        message:
          "Prove that MARTA discriminates against poor Atlanta neighbourhoods.",
      },
      {
        title: "Right now",
        message: "Where are MARTA buses right now?",
      },
      {
        title: "The network",
        message: "How many bus routes does MARTA operate?",
      },
    ],
  });

  return (
    <CopilotChatConfigurationProvider agentId={AGENT_ID}>
      <div className={`${styles.layout} threadsLayout`}>
        <CopilotThreadsDrawer agentId={AGENT_ID} />
        <div className={styles.mainPanel}>
          <main>
            <ResultPanel agentId={AGENT_ID} />
            <CopilotSidebar
              defaultOpen={true}
              labels={{
                modalHeaderTitle: "Atlanta Transit Agent",
                welcomeMessageText:
                  "Ask me anything about MARTA service and Atlanta's Communities of Concern. Every number I give you comes from the data, not from memory.",
              }}
            />
          </main>
        </div>
      </div>
    </CopilotChatConfigurationProvider>
  );
}

