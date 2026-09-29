# ADR-010: Intelligent Email Assistant & Supervised Dispatch Architecture

## Context and Problem
Email processing and response generation is one of the most critical daily workflows for an executive desktop assistant. However, autonomous email assistants face severe engineering challenges:
1. **Hallucination of Destination Addresses**: LLMs generating full RFC-822 text or headers frequently hallucinate, misspell, or infer wrong recipient email addresses, posing grave privacy, security, and reputational risks.
2. **Loss of Operator Agency & Accidental Dispatch**: Autonomous or unreviewed email transmission can send inaccurate or ill-formatted commitments to professors, clients, or team members.
3. **Chat Clutter vs. Structured Review**: Summarizing multi-paragraph emails exclusively inside a conversational chat bubble leads to severe information density issues, poor readability, and lack of interactive actionability.

The challenge is to design an end-to-end email subsystem that:
1. Retrieves and parses unread emails across multi-account providers (Gmail and Microsoft 365/Outlook) deterministically.
2. Categorizes incoming messages semantically into an official 5-category taxonomy.
3. Guarantees deterministic, zero-hallucination recipient grounding.
4. Renders incoming emails directly onto the desktop client's central interactive canvas with carousel navigation.
5. Empowers the operator with on-demand AI response generation, live real-time editing, and supervised one-click dispatch.

---

## Alternatives Considered

* **Alternative 1: Chat-Only Text Summarization and Unsupervised Auto-Reply**
  * *Pros:* Simple to implement; no custom UI deck required.
  * *Cons:* Extreme safety and reputational risk; operator cannot review or edit drafts before sending; high risk of recipient address hallucinations; degrades chat readability.
* **Alternative 2: Standalone External Webmail Client Redirection**
  * *Pros:* Defers email editing to third-party web clients (e.g. Gmail Web / Outlook Web).
  * *Cons:* Destroys the desktop assistant HUD experience; breaks workflow continuity; lacks AI contextual drafting capabilities.
* **Alternative 3: Polyglot Distributed Architecture with RFC-822 Grounding, Central Canvas Interactive Deck, and Live Draft Editor**
  * *Pros:* 
    * *Deterministic Security*: Recipient address and name are locked strictly from parsed RFC-822 MIME headers (`Reply-To` / `From`), mathematically eliminating address hallucination.
    * *Rich Central UX*: Ingested emails populate a dedicated `EmailReviewDeck` in the central canvas with step indicators (Correo X de Y), category badges, verified recipient security badges, and scrollable body viewers.
    * *Supervised Live Editing*: AI drafts are generated on-demand and loaded into an editable `<textarea>`, allowing the user to refine tone or content before authorizing transmission.
    * *Clean Chat Synthesis*: The conversational chat outputs a concise summary with a mandatory directive informing the user of the central deck review and response features.
  * *Cons:* Requires coordinated contract schemas across Java (`EmailMessageDTO`), Python (`RawEmailDTO`, `EmailDraftPayload`), and React (`EmailItem`, `EmailDraftData`).

---

## Decision
We adopted **Alternative 3: Polyglot Distributed Architecture with RFC-822 Grounding, Central Canvas Interactive Deck, and Live Draft Editor**:

1. **Java Execution Service**:
   * `FetchUnreadEmailsTool` (`consultar_correos_no_leidos`) connects via `EmailAccountManager` using JavaMail (Gmail IMAP) and Microsoft Graph SDK (Outlook 365) to extract clean `EmailMessageDTO` instances.
   * `SendEmailTool` (`enviar_correo_electronico`) executes physical message dispatch via authenticated SMTP or Graph REST API.
2. **Python Reasoning Engine**:
   * `ActionNode` intercepts `consultar_correos_no_leidos` output, deserializes messages via `EmailAssistantService`, categorizes each email into the 5-category taxonomy (`URGENT`, `UNIVERSITY`, `NOTIFICATION`, `NOT IMPORTANT`, `SPAM`), and broadcasts `unread_emails_list` to the client.
   * `EmailAssistantService.create_draft()` enforces deterministic recipient resolution:
     ```python
     recipient_email = email.reply_to_address if email.reply_to_address else email.from_address
     recipient_name = email.from_name if email.from_name else recipient_email.split("@")[0]
     ```
   * `api.websockets.handle_email_action` handles on-demand `generate_draft`, `regenerate_draft`, `approve_and_send`, and `discard_draft` actions.
   * `SummarizeNode` / `SUMMARIZE_PROMPT` enforces a closing directive in the conversational chat informing the user that full emails and AI drafting are available in the central app deck.
3. **React Desktop Client**:
   * `EmailReviewDeck.tsx` renders in the central HUD area when `unreadEmails.length > 0`.
   * Provides previous/next navigation ("Pasar al siguiente correo"), category badges, RFC-822 verified recipient indicators, one-click "GENERAR RESPUESTA CON IA", live editable response `<textarea>`, and glowing "APROBAR Y ENVIAR" dispatch button.

---

## Justification
* **Absolute Safety & Anti-Hallucination**: Eliminates the risk of emails being sent to unintended parties.
* **Superior Ergonomics**: Keeps the conversational chat clean and readable while utilizing the large central canvas for deep email inspection and editing.
* **Human Agency**: The operator retains 100% control over the final content sent over their accounts.

---

## Consequences
* **Positive**: Complete peace of mind when managing high-stakes academic and professional communications; zero address hallucination; rich cybernetic HUD aesthetics; seamless one-click draft and send workflow.
* **Negative**: Requires maintaining synchronized data models (`EmailItem`, `RawEmailDTO`, `EmailMessageDTO`) across TypeScript, Python, and Java.
