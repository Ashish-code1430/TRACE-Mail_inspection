
import html
import ipaddress
import json
import re
import tempfile
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import urlparse

import gradio as gr
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

PROJECT_DIR = Path(__file__).resolve().parent
MODEL_DIR = PROJECT_DIR / "03_Models" / "TRACE_Mail_CPU_5000"
REPORT_DIR = PROJECT_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

if not MODEL_DIR.exists():
    MODEL_DIR = Path("/content/drive1/MyDrive/TRACE-Mail-Project/03_Models/TRACE_Mail_CPU_5000")

if not MODEL_DIR.exists():
    raise FileNotFoundError(
        "Model directory not found. Place TRACE_Mail_CPU_5000 inside "
        "the 03_Models folder next to app.py, or update MODEL_DIR."
    )

tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
model = AutoModelForSequenceClassification.from_pretrained(
    str(MODEL_DIR),
    local_files_only=True
)
model.to("cpu")
model.eval()

CSS = """
:root {
    color-scheme: dark;
}
.gradio-container {
    max-width: 1450px !important;
    margin: auto !important;
}
#trace-hero {
    padding: 30px;
    border-radius: 22px;
    background: linear-gradient(120deg, #111827, #172554 65%, #312e81);
    border: 1px solid #334155;
    margin-bottom: 18px;
}
#trace-hero h1 {
    font-size: 38px;
    color: #f8fafc;
    margin-bottom: 8px;
}
#trace-hero p {
    color: #cbd5e1;
    font-size: 16px;
}
.trace-card {
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 19px;
    background: #111827;
    min-height: 115px;
}
.trace-label {
    color: #94a3b8;
    font-size: 13px;
    margin-bottom: 10px;
}
.trace-value {
    font-size: 28px;
    font-weight: 800;
    color: #f8fafc;
}
.trace-muted {
    color: #94a3b8;
    font-size: 12px;
    margin-top: 8px;
}
.trace-section {
    padding: 17px;
    border: 1px solid #334155;
    border-radius: 15px;
    background: #111827;
}
.trace-finding {
    padding: 13px;
    border-radius: 10px;
    background: #1e293b;
    border-left: 4px solid #f97316;
    margin: 9px 0;
}
.trace-badge {
    display: inline-block;
    padding: 4px 9px;
    border-radius: 99px;
    font-size: 12px;
    font-weight: 700;
    margin-left: 6px;
}
.trace-high {
    color: #fecaca;
    background: #7f1d1d;
}
.trace-medium {
    color: #fed7aa;
    background: #7c2d12;
}
.trace-low {
    color: #bbf7d0;
    background: #14532d;
}
.trace-email {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    line-height: 1.8;
    padding: 18px;
    border-radius: 12px;
    background: #0f172a;
    border: 1px solid #334155;
    color: #e2e8f0;
}
.trace-note {
    padding: 12px;
    border-radius: 10px;
    background: #172033;
    border: 1px solid #475569;
    color: #cbd5e1;
    font-size: 13px;
}
"""

def card(label, value, detail="", color="#f8fafc"):
    return f"""
    <div class="trace-card">
      <div class="trace-label">{html.escape(str(label))}</div>
      <div class="trace-value" style="color:{color}">
        {html.escape(str(value))}
      </div>
      <div class="trace-muted">{html.escape(str(detail))}</div>
    </div>
    """

def get_domain(address):
    parsed = parseaddr(address or "")[1]
    if "@" not in parsed:
        return ""
    return parsed.rsplit("@", 1)[1].lower().strip(".")

def calculate_risk(score):
    if score <= 0:
        return 0, "Low"
    if score <= 2:
        return 25, "Low"
    if score <= 4:
        return 50, "Medium"
    if score <= 6:
        return 75, "High"
    return 90, "High"

def extract_email(path):
    with open(path, "rb") as file:
        message = BytesParser(policy=policy.default).parse(file)

    parts = []

    for part in message.walk():
        if part.get_content_disposition() == "attachment":
            continue

        if part.get_content_type() != "text/plain":
            continue

        try:
            content = part.get_content()
            if isinstance(content, str):
                parts.append(content)
        except Exception:
            continue

    if not parts and not message.is_multipart():
        try:
            content = message.get_content()
            if isinstance(content, str):
                parts.append(content)
        except Exception:
            pass

    return {
        "subject": str(message.get("Subject", "") or ""),
        "sender": str(message.get("From", "") or ""),
        "reply_to": str(message.get("Reply-To", "") or ""),
        "date": str(message.get("Date", "") or ""),
        "body": "\n".join(parts),
        "message_id": str(message.get("Message-ID", "") or "")
    }

def find_risky_words(text):
    patterns = {
        "Urgency": [
            r"\burgent\b",
            r"\bimmediately\b",
            r"\bact now\b",
            r"\bexpires today\b",
            r"\bsuspended\b",
            r"\bfinal warning\b",
            r"\bwithin 24 hours\b",
            r"\bright away\b"
        ],
        "Credential request": [
            r"\bpassword\b",
            r"\bcredentials\b",
            r"\bverify your account\b",
            r"\bconfirm your password\b",
            r"\blogin details\b",
            r"\bpasscode\b",
            r"\bone-time password\b",
            r"\bOTP\b"
        ],
        "Financial pressure": [
            r"\bwire transfer\b",
            r"\bpayment required\b",
            r"\bpay immediately\b",
            r"\boverdue invoice\b",
            r"\bgift card\b"
        ],
        "Sensitive information": [
            r"\bcredit card number\b",
            r"\bsecurity code\b",
            r"\bsocial security number\b",
            r"\bpersonal information\b"
        ],
        "Link and attachment language": [
            r"\bclick here\b",
            r"\bopen the attachment\b",
            r"\bdownload the file\b",
            r"\bverify using this link\b",
            r"\breset your password\b"
        ]
    }

    matches = []

    for category, expressions in patterns.items():
        for expression in expressions:
            for match in re.finditer(expression, text, re.I):
                matches.append({
                    "category": category,
                    "term": match.group(0),
                    "start": match.start(),
                    "end": match.end()
                })

    matches.sort(key=lambda item: (item["start"], -item["end"]))

    selected = []
    last_end = -1

    for item in matches:
        if item["start"] < last_end:
            continue
        selected.append(item)
        last_end = item["end"]

    return selected

def highlight_text(text, matches):
    pieces = []
    cursor = 0

    for item in matches:
        pieces.append(html.escape(text[cursor:item["start"]]))
        pieces.append(
            '<mark title="' + html.escape(item["category"]) + '" '
            'style="background:#7f1d1d;color:#fecaca;'
            'padding:2px 5px;border-radius:5px;'
            'font-weight:700;border:1px solid #ef4444">'
            + html.escape(text[item["start"]:item["end"]])
            + '</mark>'
        )
        cursor = item["end"]

    pieces.append(html.escape(text[cursor:]))
    return "".join(pieces)

def analyze_email(file_path):
    if not file_path:
        raise gr.Error("Please paste an email or upload an .eml file.")

    path = Path(file_path)

    if not path.is_file() or path.suffix.lower() != ".eml":
        raise gr.Error("Please provide a valid .eml file or paste email text.")

    try:
        email_data = extract_email(path)

        subject = email_data["subject"]
        sender = email_data["sender"]
        reply_to = email_data["reply_to"]
        body = email_data["body"]
        full_text = f"Subject: {subject}\n{body}".strip()

        if not full_text.strip():
            raise gr.Error("No readable email text was found.")

        inputs = tokenizer(
            full_text,
            return_tensors="pt",
            truncation=True,
            max_length=128
        )

        with torch.no_grad():
            outputs = model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=-1)[0]

        predicted_class = int(torch.argmax(probabilities).item())
        class_probabilities = {
            f"Class {i}": round(float(probabilities[i].item()) * 100, 2)
            for i in range(len(probabilities))
        }
        model_confidence = class_probabilities[f"Class {predicted_class}"]

        findings = []
        score = 0
        header_findings = []
        urls = []

        sender_domain = get_domain(sender)
        reply_domain = get_domain(reply_to)

        if sender_domain and reply_domain and sender_domain != reply_domain:
            header_findings.append({
                "indicator": "Sender and Reply-To domain mismatch",
                "severity": "medium",
                "points": 2,
                "sender_domain": sender_domain,
                "reply_to_domain": reply_domain,
                "explanation": "The reply address uses a different domain."
            })

        for item in header_findings:
            findings.append(item)
            score += item["points"]

        url_pattern = r"https?://[^\s<>\"']+|www\.[^\s<>\"']+"
        seen_urls = set()

        for match in re.finditer(url_pattern, full_text, re.I):
            raw_url = match.group(0).rstrip(".,;:!?)\u005d")

            if raw_url in seen_urls:
                continue

            seen_urls.add(raw_url)
            normalized = raw_url if raw_url.lower().startswith(("http://", "https://")) else "http://" + raw_url
            parsed = urlparse(normalized)
            hostname = parsed.hostname or ""
            indicators = []

            if parsed.scheme.lower() == "http":
                indicators.append("Uses unencrypted HTTP")
                findings.append({
                    "indicator": "Unencrypted HTTP URL",
                    "severity": "medium",
                    "points": 2,
                    "explanation": "The URL does not use HTTPS.",
                    "observed": raw_url
                })
                score += 2

            is_ip = False

            try:
                ipaddress.ip_address(hostname)
                is_ip = True
            except ValueError:
                pass

            if is_ip:
                indicators.append("Uses an IP address")
                findings.append({
                    "indicator": "URL uses an IP address",
                    "severity": "medium",
                    "points": 2,
                    "explanation": "The URL hostname is a numeric IP address.",
                    "observed": hostname
                })
                score += 2

            urls.append({
                "url": raw_url,
                "hostname": hostname,
                "scheme": parsed.scheme,
                "uses_http": parsed.scheme.lower() == "http",
                "uses_ip_address": is_ip,
                "indicators": indicators
            })

        risky_matches = find_risky_words(full_text)
        categorized_terms = {}

        for item in risky_matches:
            categorized_terms.setdefault(item["category"], [])
            if item["term"] not in categorized_terms[item["category"]]:
                categorized_terms[item["category"]].append(item["term"])

        category_weights = {
            "Urgency": 1,
            "Credential request": 2,
            "Financial pressure": 2,
            "Sensitive information": 2,
            "Link and attachment language": 1
        }

        for category, terms in categorized_terms.items():
            points = category_weights[category]
            findings.append({
                "indicator": f"{category} language",
                "severity": "low" if points == 1 else "medium",
                "points": points,
                "explanation": "Potentially risky wording was found. Context is required to determine intent.",
                "observed": terms
            })
            score += points

        risk_percentage, risk_level = calculate_risk(score)

        if risk_level == "High":
            risk_color = "#ef4444"
        elif risk_level == "Medium":
            risk_color = "#f59e0b"
        else:
            risk_color = "#22c55e"

        risk_html = f"""
        <div class="trace-section">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap">
            <div>
              <div class="trace-label">PRELIMINARY HEURISTIC RISK</div>
              <div style="font-size:46px;font-weight:900;color:{risk_color}">
                {risk_percentage}%
              </div>
              <div style="font-size:18px;font-weight:700;color:{risk_color}">
                {risk_level} Risk
              </div>
            </div>
            <div style="min-width:180px;flex:1">
              <div style="height:13px;background:#334155;border-radius:20px;overflow:hidden">
                <div style="height:13px;width:{risk_percentage}%;background:{risk_color};border-radius:20px"></div>
              </div>
              <div class="trace-muted">Rule-based visual score, not a probability of maliciousness.</div>
            </div>
          </div>
        </div>
        """

        summary_html = f"""
        <div class="trace-section">
          <h2 style="margin-top:0">Analysis Overview</h2>
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:12px">
            {card("Predicted class", f"CLASS_{predicted_class}", "Dataset label meaning unverified", "#93c5fd")}
            {card("Model confidence", f"{model_confidence:.2f}%", "Score for predicted class", "#a5b4fc")}
            {card("Heuristic score", score, "Sum of rule-based points", risk_color)}
            {card("URLs detected", len(urls), "Unique URLs found", "#fbbf24")}
            {card("Indicators", len(findings), "Observed rule matches", "#fb923c")}
          </div>
          <p class="trace-note" style="margin-top:14px">
            Model confidence and heuristic risk are different measurements.
            Class meanings have not been verified against the dataset documentation.
          </p>
        </div>
        """

        email_display = f"""
        <div class="trace-section">
          <h3 style="margin-top:0">Email Details</h3>
          <p><b>Subject:</b> {html.escape(subject or "(no subject)")}</p>
          <p><b>From:</b> {html.escape(sender or "(not provided)")}</p>
          <p><b>Reply-To:</b> {html.escape(reply_to or "(not provided)")}</p>
          <p><b>Date:</b> {html.escape(email_data["date"] or "(not provided)")}</p>
          <div class="trace-email">{highlight_text(full_text, risky_matches)}</div>
          <p class="trace-muted">Red highlights indicate phrases matched by the local rule-based word detector.</p>
        </div>
        """

        if findings:
            finding_cards = []

            for item in findings:
                severity = item.get("severity", "low")
                badge_class = "trace-" + severity
                observed = item.get("observed", "")

                if isinstance(observed, (list, dict)):
                    observed = json.dumps(observed, ensure_ascii=False)

                finding_cards.append(f"""
                <div class="trace-finding">
                  <div style="font-weight:750">
                    {html.escape(item["indicator"])}
                    <span class="trace-badge {badge_class}">{html.escape(severity.upper())}</span>
                    <span class="trace-badge">+{item.get("points", 0)} points</span>
                  </div>
                  <div style="color:#cbd5e1;margin-top:6px">{html.escape(item.get("explanation", ""))}</div>
                  <div class="trace-muted">Evidence: {html.escape(str(observed))}</div>
                </div>
                """)

            findings_html = (
                "<div class='trace-section'><h3>Forensic Findings</h3>"
                + "".join(finding_cards) + "</div>"
            )
        else:
            findings_html = (
                "<div class='trace-section'><h3>Forensic Findings</h3>"
                "<p>No indicators were detected by the current rules. "
                "This does not establish that the email is safe.</p></div>"
            )

        url_rows = []

        for item in urls:
            indicator_text = ", ".join(item["indicators"]) or "No URL rule triggered"
            url_rows.append([
                item["url"],
                item["hostname"],
                item["scheme"],
                indicator_text
            ])

        if categorized_terms:
            phrase_html = "".join(
                "<div class='trace-finding'><b>" + html.escape(category) +
                "</b><div style='margin-top:6px'>" +
                ", ".join(html.escape(term) for term in terms) +
                "</div></div>"
                for category, terms in categorized_terms.items()
            )
        else:
            phrase_html = "<p>No terms matched the current risky-word rules.</p>"

        recommended_actions = [
            "Do not enter credentials through an unexpected email link.",
            "Verify unusual requests using a trusted contact method obtained independently.",
            "Inspect authentication headers in a trusted mail system.",
            "Do not open suspicious links or attachments to test them."
        ]

        report = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "model": MODEL_DIR.name,
            "predicted_class": predicted_class,
            "model_confidence_percent": model_confidence,
            "class_scores_percent": class_probabilities,
            "label_interpretation": "Class meanings are not verified.",
            "email": {
                "filename": path.name,
                "subject": subject,
                "sender": sender,
                "reply_to": reply_to,
                "date": email_data["date"],
                "body": body
            },
            "heuristic_assessment": {
                "risk_percentage": risk_percentage,
                "risk_level": risk_level,
                "heuristic_score": score,
                "interpretation": "Rule-based visual scale, not a calibrated probability of maliciousness."
            },
            "findings": findings,
            "header_findings": header_findings,
            "urls": urls,
            "risky_terms_by_category": categorized_terms,
            "recommended_actions": recommended_actions,
            "limitations": [
                "Dataset class meanings have not been verified.",
                "Model scores are not calibrated probabilities of maliciousness.",
                "The heuristic risk percentage is a display scale based on rule points.",
                "Word matching can produce false positives and false negatives.",
                "Only a limited number of tokens are processed by the model.",
                "URL destinations are not opened or tested.",
                "Email authentication results are not independently verified."
            ]
        }

        report_path = REPORT_DIR / (
            "TRACE_Mail_Report_" +
            datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f") +
            ".json"
        )

        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        return (
            summary_html,
            risk_html,
            email_display,
            findings_html,
            url_rows,
            report,
            str(report_path)
        )

    except gr.Error:
        raise
    except Exception as error:
        error_html = (
            "<div class='trace-section'><h3>Analysis failed</h3>"
            "<p>" + html.escape(type(error).__name__) + ": " +
            html.escape(str(error)) + "</p></div>"
        )
        return (
            error_html,
            "",
            "<div class='trace-note'>Email display unavailable.</div>",
            "<div class='trace-note'>Findings unavailable.</div>",
            [],
            {"error": type(error).__name__, "message": str(error)},
            None
        )

def analyze_email_input(uploaded_file, pasted_email):
    if pasted_email and pasted_email.strip():
        email_content = pasted_email.strip()

        if not re.search(
            r"(?m)^(From|To|Cc|Bcc|Date|Subject|Reply-To|Message-ID):",
            email_content
        ):
            email_content = "Subject: Pasted email\n\n" + email_content
        elif "\n\n" not in email_content and "\r\n\r\n" not in email_content:
            email_content += "\n\n"

        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".eml",
                encoding="utf-8",
                newline="",
                delete=False
            ) as temp_file:
                temp_file.write(email_content)
                temp_path = temp_file.name

            return analyze_email(temp_path)

        finally:
            if temp_path and Path(temp_path).exists():
                Path(temp_path).unlink()

    if uploaded_file:
        return analyze_email(uploaded_file)

    raise gr.Error("Please paste an email or upload an .eml file.")

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

    with gr.Row():
        with gr.Column(scale=1):
            email_file = gr.File(
                label="Upload an email file (.eml)",
                file_types=[".eml"],
                type="filepath"
            )

            email_text = gr.Textbox(
                label="Or paste your email here",
                placeholder="Paste your complete email here...\n\nFrom: sender@example.com\nTo: recipient@example.com\nSubject: Urgent account verification\n\nEmail body...",
                lines=12,
                max_lines=25
            )

            analyze_button = gr.Button(
                "🔍 Analyze Email",
                variant="primary",
                size="lg"
            )

            gr.Markdown(
                "Paste an email or upload an .eml file. "
                "Suspicious links are not opened."
            )

        with gr.Column(scale=2):
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

    gr.Markdown("""
    <div class="trace-note">
    <b>Important limitations:</b> The model's class meanings are unverified.
    Model confidence is not a threat probability. The heuristic risk percentage
    is a visual scale derived from rule-based points, not a calibrated probability.
    Results support review and do not prove maliciousness.
    </div>
    """)

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
    import os

demo.launch(
    server_name="0.0.0.0",
    server_port=int(os.environ.get("PORT", "10000")),
    share=False,
    debug=False
)

