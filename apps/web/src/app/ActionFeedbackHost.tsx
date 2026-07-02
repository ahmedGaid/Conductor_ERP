import { useActionFeedbackState } from "./ActionFeedbackContext";
import { ActionReceiptCard } from "./ActionReceiptCard";
import { useFeedbackMode } from "../lib/feedbackMode";
import "./ActionFeedbackHost.css";

/**
 * Renders the one live ActionReceipt as a floating card in the block-end / inline-end corner. The
 * user's chosen depth (simple / rich) is passed through to the card. Mounted once in the app shell.
 */
export function ActionFeedbackHost() {
  const { receipt, dismiss, pause, resume } = useActionFeedbackState();
  const detail = useFeedbackMode();

  if (!receipt) return null;

  return (
    <div className="arf arf--floating">
      <ActionReceiptCard
        receipt={receipt}
        detail={detail}
        onDismiss={() => dismiss(receipt.id)}
        onPause={pause}
        onResume={resume}
      />
    </div>
  );
}
