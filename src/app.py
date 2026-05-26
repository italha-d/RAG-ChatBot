from __future__ import annotations

import gradio as gr

import config
from src.agent import ask
from src.ingest_service import (
    accepted_upload_suffixes,
    clear_knowledge_base,
    ingest_uploads,
)
from src.ollama_models import (
    ModelLists,
    default_chat_choice,
    default_embed_choice,
    list_models,
)
from src.store import collection_count, get_collection, indexed_embed_model

CUSTOM_CSS = """
.gradio-container { max-width: 1200px !important; margin: auto; }
#chat-panel { min-height: 520px; }
.status-box { font-size: 0.95rem; }
footer { display: none !important; }
"""

FILE_TYPES = sorted(accepted_upload_suffixes())


def _format_model_status(lists: ModelLists, embed: str | None, chat: str | None) -> str:
    lines: list[str] = []
    if lists.error:
        lines.append(f"**Ollama:** {lists.error}")
    else:
        lines.append("**Ollama:** connected")
        lines.append(
            f"- Embedding models installed: **{len(lists.embedding_models)}**"
        )
        lines.append(f"- Chat models installed: **{len(lists.chat_models)}**")

    if embed:
        lines.append(f"- **Selected embed:** `{embed}`")
    if chat:
        lines.append(f"- **Selected chat:** `{chat}`")

    indexed = indexed_embed_model()
    if indexed:
        lines.append(f"- **Indexed with:** `{indexed}`")
        if embed and indexed != embed:
            lines.append(
                "  - Warning: selected embed model differs from the index. "
                "Re-ingest with **Replace entire knowledge base**."
            )

    return "\n".join(lines)


def index_status() -> str:
    try:
        total = collection_count(get_collection())
    except Exception as exc:
        return f"**Knowledge base:** unavailable ({exc})"
    return f"**Knowledge base:** {total} chunk(s) indexed"


def sidebar_status(embed_model: str | None, chat_model: str | None) -> str:
    lists = list_models()
    return (
        f"{_format_model_status(lists, embed_model, chat_model)}\n\n{index_status()}"
    )


def refresh_model_dropdowns(
    current_embed: str | None = None,
    current_chat: str | None = None,
) -> tuple[dict, dict, str]:
    lists = list_models(refresh=True)
    embed_choices = lists.embedding_models or [config.OLLAMA_EMBED_MODEL]
    chat_choices = lists.chat_models or [config.OLLAMA_CHAT_MODEL]

    embed_default = default_embed_choice(lists) or embed_choices[0]
    chat_default = default_chat_choice(lists) or chat_choices[0]

    if current_embed and current_embed in embed_choices:
        embed_default = current_embed
    if current_chat and current_chat in chat_choices:
        chat_default = current_chat

    status = sidebar_status(embed_default, chat_default)
    if lists.error:
        status = f"**Error:** {lists.error}\n\n{status}"

    return (
        gr.update(choices=embed_choices, value=embed_default),
        gr.update(choices=chat_choices, value=chat_default),
        status,
    )


def load_model_dropdowns() -> tuple[dict, dict, str]:
    return refresh_model_dropdowns()


def handle_ingest(
    files,
    reset_index: bool,
    embed_model: str,
) -> str:
    paths: list[str] = []
    if files:
        for item in files:
            path = item if isinstance(item, str) else getattr(item, "name", None)
            if path:
                paths.append(path)

    if not paths:
        return "Drop files above, then click **Add to knowledge base**."

    try:
        result = ingest_uploads(
            paths,
            reset=reset_index,
            embed_model=embed_model or None,
        )
    except ValueError as exc:
        return f"**Ingest failed:** {exc}"

    lines = [result.summary()]
    if result.skipped:
        lines.append("\n**Skipped (no extractable text):** " + ", ".join(result.skipped))
    lines.append(f"\n**Embedding model used:** `{embed_model}`")
    lines.append("\n" + index_status())
    return "\n".join(lines)


def handle_clear_kb(delete_files: bool, embed_model: str, chat_model: str) -> str:
    remaining = clear_knowledge_base(delete_uploads=delete_files)
    msg = f"Knowledge base cleared. Chunks remaining: {remaining}."
    if delete_files:
        msg += " Uploaded copies removed."
    return msg + "\n\n" + sidebar_status(embed_model, chat_model)


def handle_chat(
    message: str,
    history: list[dict[str, str]],
    chat_model: str,
    embed_model: str,
) -> tuple[list[dict[str, str]], str]:
    if not message or not message.strip():
        return history, sidebar_status(embed_model, chat_model)

    result = ask(message.strip(), model=chat_model or None)
    answer = result["answer"]
    if result.get("warnings"):
        warn = "\n".join(f"> {w}" for w in result["warnings"])
        answer = f"{answer}\n\n---\n**Quote checks**\n{warn}"

    history = list(history or [])
    history.append({"role": "user", "content": message.strip()})
    history.append({"role": "assistant", "content": answer})
    return history, sidebar_status(embed_model, chat_model)


def handle_clear_chat(embed_model: str, chat_model: str) -> tuple[list[dict[str, str]], str]:
    return [], sidebar_status(embed_model, chat_model)


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Local RAG Chatbot") as demo:
        gr.Markdown(
            "# Local RAG Chatbot\n"
            "Drag and drop documents, build a knowledge base, then chat. "
            "Everything runs on your machine with **Ollama** — no cloud required."
        )

        with gr.Row(equal_height=False):
            with gr.Column(scale=1, min_width=320):
                gr.Markdown("### Models")
                embed_model_dd = gr.Dropdown(
                    label="Embedding model",
                    choices=[],
                    value=None,
                    interactive=True,
                    info="For indexing documents (from `ollama list`)",
                )
                chat_model_dd = gr.Dropdown(
                    label="Chat model",
                    choices=[],
                    value=None,
                    interactive=True,
                    info="For answering questions (from `ollama list`)",
                )
                refresh_models_btn = gr.Button("Refresh model list", variant="secondary")

                gr.Markdown("### Documents")
                file_upload = gr.File(
                    label="Drop files here",
                    file_count="multiple",
                    file_types=FILE_TYPES,
                    type="filepath",
                )
                reset_on_ingest = gr.Checkbox(
                    label="Replace entire knowledge base (instead of adding)",
                    value=False,
                )
                ingest_btn = gr.Button("Add to knowledge base", variant="primary")
                ingest_log = gr.Markdown("Drop files above, then click **Add to knowledge base**.")

                gr.Markdown("### Manage")
                delete_uploads = gr.Checkbox(
                    label="Also delete saved uploads when clearing",
                    value=False,
                )
                clear_kb_btn = gr.Button("Clear knowledge base", variant="secondary")
                status_panel = gr.Markdown("", elem_classes=["status-box"])

            with gr.Column(scale=2, elem_id="chat-panel"):
                gr.Markdown("### Chat")
                chatbot = gr.Chatbot(
                    label="Ask about your documents",
                    height=480,
                )
                with gr.Row():
                    msg = gr.Textbox(
                        label="Your question",
                        placeholder="e.g. What is the refund policy?",
                        scale=4,
                        lines=2,
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)
                clear_chat_btn = gr.Button("Clear chat", variant="secondary")

        model_outputs = [embed_model_dd, chat_model_dd, status_panel]

        refresh_models_btn.click(
            refresh_model_dropdowns,
            inputs=[embed_model_dd, chat_model_dd],
            outputs=model_outputs,
        )

        demo.load(load_model_dropdowns, outputs=model_outputs)

        embed_model_dd.change(
            sidebar_status,
            inputs=[embed_model_dd, chat_model_dd],
            outputs=[status_panel],
        )
        chat_model_dd.change(
            sidebar_status,
            inputs=[embed_model_dd, chat_model_dd],
            outputs=[status_panel],
        )

        ingest_btn.click(
            handle_ingest,
            inputs=[file_upload, reset_on_ingest, embed_model_dd],
            outputs=[ingest_log],
        ).then(
            sidebar_status,
            inputs=[embed_model_dd, chat_model_dd],
            outputs=[status_panel],
        )

        clear_kb_btn.click(
            handle_clear_kb,
            inputs=[delete_uploads, embed_model_dd, chat_model_dd],
            outputs=[ingest_log],
        ).then(
            sidebar_status,
            inputs=[embed_model_dd, chat_model_dd],
            outputs=[status_panel],
        )

        submit = [msg, chatbot, chat_model_dd, embed_model_dd]
        send_btn.click(handle_chat, submit, [chatbot, status_panel]).then(
            lambda: "", outputs=[msg]
        )
        msg.submit(handle_chat, submit, [chatbot, status_panel]).then(
            lambda: "", outputs=[msg]
        )
        clear_chat_btn.click(
            handle_clear_chat,
            inputs=[embed_model_dd, chat_model_dd],
            outputs=[chatbot, status_panel],
        )

    return demo


def launch(
    *,
    host: str | None = None,
    port: int | None = None,
    share: bool = False,
) -> None:
    config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    demo = build_ui()
    demo.launch(
        server_name=host or config.APP_HOST,
        server_port=port or config.APP_PORT,
        share=share,
        show_error=True,
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(primary_hue="slate", secondary_hue="blue"),
    )


if __name__ == "__main__":
    launch()
