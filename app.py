        return analyze_email(uploaded_file)

    pasted_email = (pasted_email or "").strip()
    if not pasted_email:
        return (
            "<div class='trace-note'>Upload an .eml file or paste email content to begin.</div>",
            "",
            "<div class='trace-note'>No email analyzed yet.</div>",
            "<div class='trace-note'>No findings available.</div>",
            [],
            {},
            None
        )

    if not re.search(r"(?im)^(From|To|Cc|Bcc|Subject|Date|Reply-To|Message-ID):", pasted_email):
        pasted_email = "Subject: Pasted email\\n\\n" + pasted_email
    elif "\\n\\n" not in pasted_email and "\\r\\n\\r\\n" not in pasted_email:
        pasted_email = pasted_email.rstrip() + "\\n\\n"

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".eml",
            delete=False
        ) as temp_file:
            temp_file.write(pasted_email)
            temp_path = temp_file.name

        return analyze_email(temp_path)
    finally:
        if temp_path and Path(temp_path).exists():
            Path(temp_path).unlink()

with gr.Blocks(
    title="TRACE-Mail | Email Threat Intelligence",
    theme=gr.themes.Soft(
        primary_hue="red",
        secondary_hue="slate",
        neutral_hue="slate"
    ),
    css=CSS
) as demo:

    gr.HTML("""
    <div id="trace-hero">
      <div style="font-size:13px;letter-spacing:3px;color:#fca5a5;font-weight:800">
        EMAIL THREAT INTELLIGENCE
      </div>
      <h1>🛡️ TRACE-Mail</h1>
      <p>Deep Learning · NLP · Explainable Email Forensics</p>
      <div style="color:#cbd5e1;font-size:13px">
        Inspect email content, model output, suspicious wording, URLs, and header inconsistencies.
      </div>
    </div>
    """)

    with gr.Row(equal_height=False):
        with gr.Column(scale=1, min_width=320):
            email_file = gr.File(
                label="Upload an email file (.eml)",
                file_types=[".eml"],
                type="filepath"
            )
            email_text = gr.Textbox(
                label="Or paste email content",
                placeholder="Paste the complete email, including headers if available...",
                lines=12,
                max_lines=24
            )
            analyze_button = gr.Button(
                "🔍 Analyze Email",
                variant="primary",
                size="lg"
            )
            gr.Markdown(
                "Upload an `.eml` file or paste email content. "
                "If both are provided, the uploaded file is analyzed. "
                "Suspicious links are not opened."
            )
        with gr.Column(scale=2, min_width=420):
            summary_output = gr.HTML(label="Analysis overview")

    risk_output = gr.HTML(label="Risk indicator")

    with gr.Tab("Email Inspection"):
        email_output = gr.HTML(label="Email content and highlighted terms")

    with gr.Tab("Forensic Findings"):
        findings_output = gr.HTML(label="Explainable findings")

    with gr.Tab("URL Analysis"):
        url_output = gr.Dataframe(
            headers=["URL", "Hostname", "Scheme", "Indicators"],
            datatype=["str", "str", "str", "str"],
            label="Detected URLs",
            interactive=False
        )

    with gr.Tab("Full JSON Report"):
        report_output = gr.JSON(label="Complete analysis report")
        download_output = gr.File(label="Download JSON report")


    analyze_button.click(
        fn=analyze_email_input,
        inputs=[email_file, email_text],
        outputs=[
            summary_output,
            risk_output,
            email_output,
            findings_output,
            url_output,
            report_output,
            download_output
        ]
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "10000")),
        share=False,
        debug=False
    )
        return analyze_email(uploaded_file)

    pasted_email = (pasted_email or "").strip()
    if not pasted_email:
        return (
            "<div class='trace-note'>Upload an .eml file or paste email content to begin.</div>",
            "",
            "<div class='trace-note'>No email analyzed yet.</div>",
            "<div class='trace-note'>No findings available.</div>",
            [],
            {},
            None
        )

    if not re.search(r"(?im)^(From|To|Cc|Bcc|Subject|Date|Reply-To|Message-ID):", pasted_email):
        pasted_email = "Subject: Pasted email\\n\\n" + pasted_email
    elif "\\n\\n" not in pasted_email and "\\r\\n\\r\\n" not in pasted_email:
        pasted_email = pasted_email.rstrip() + "\\n\\n"

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".eml",
            delete=False
        ) as temp_file:
            temp_file.write(pasted_email)
            temp_path = temp_file.name

        return analyze_email(temp_path)
    finally:
        if temp_path and Path(temp_path).exists():
            Path(temp_path).unlink()

with gr.Blocks(
    title="TRACE-Mail | Email Threat Intelligence",
    theme=gr.themes.Soft(
        primary_hue="red",
        secondary_hue="slate",
        neutral_hue="slate"
    ),
    css=CSS
) as demo:

    gr.HTML("""
    <div id="trace-hero">
      <div style="font-size:13px;letter-spacing:3px;color:#fca5a5;font-weight:800">
        EMAIL THREAT INTELLIGENCE
      </div>
      <h1>🛡️ TRACE-Mail</h1>
      <p>Deep Learning · NLP · Explainable Email Forensics</p>
      <div style="color:#cbd5e1;font-size:13px">
        Inspect email content, model output, suspicious wording, URLs, and header inconsistencies.
      </div>
    </div>
    """)

    with gr.Row(equal_height=False):
        with gr.Column(scale=1, min_width=320):
            email_file = gr.File(
                label="Upload an email file (.eml)",
                file_types=[".eml"],
                type="filepath"
            )
            email_text = gr.Textbox(
                label="Or paste email content",
                placeholder="Paste the complete email, including headers if available...",
                lines=12,
                max_lines=24
            )
            analyze_button = gr.Button(
                "🔍 Analyze Email",
                variant="primary",
                size="lg"
            )
            gr.Markdown(
                "Upload an `.eml` file or paste email content. "
                "If both are provided, the uploaded file is analyzed. "
                "Suspicious links are not opened."
            )
        with gr.Column(scale=2, min_width=420):
            summary_output = gr.HTML(label="Analysis overview")

    risk_output = gr.HTML(label="Risk indicator")

    with gr.Tab("Email Inspection"):
        email_output = gr.HTML(label="Email content and highlighted terms")

    with gr.Tab("Forensic Findings"):
        findings_output = gr.HTML(label="Explainable findings")

    with gr.Tab("URL Analysis"):
        url_output = gr.Dataframe(
            headers=["URL", "Hostname", "Scheme", "Indicators"],
            datatype=["str", "str", "str", "str"],
            label="Detected URLs",
            interactive=False
        )

    with gr.Tab("Full JSON Report"):
        report_output = gr.JSON(label="Complete analysis report")
        download_output = gr.File(label="Download JSON report")


    analyze_button.click(
        fn=analyze_email_input,
        inputs=[email_file, email_text],
        outputs=[
            summary_output,
            risk_output,
            email_output,
            findings_output,
            url_output,
            report_output,
            download_output
        ]
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "10000")),
        share=False,
        debug=False
    )
