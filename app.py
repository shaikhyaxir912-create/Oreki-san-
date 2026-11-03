import os
import json
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.environ.get("PORT", "8000"))
API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Oreki San AI</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#0d1018;color:#f4f5fb;font:16px Arial,sans-serif}
header{padding:17px;text-align:center;border-bottom:1px solid #303746;font-weight:bold}
header span{color:#8c9cff}
#chat{max-width:850px;margin:auto;padding:20px 14px 110px;min-height:80vh}
.welcome{text-align:center;margin:12vh auto 30px}
.welcome h1{font-size:32px;margin-bottom:8px}
.welcome p{color:#aab2c2}
.msg{padding:13px 16px;margin:12px 0;border-radius:16px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.5}
.user{background:#253b63;margin-left:auto;max-width:90%;width:fit-content}
.ai{background:#1b222e;border:1px solid #303746;max-width:95%}
#bottom{position:fixed;bottom:0;left:0;right:0;padding:12px;background:#0d1018;border-top:1px solid #303746}
form{max-width:850px;margin:auto;display:flex;gap:8px}
textarea{flex:1;resize:none;max-height:130px;padding:13px;border:1px solid #394355;border-radius:15px;background:#1b222e;color:white;font:inherit}
button{border:0;border-radius:14px;padding:0 18px;background:#647cff;color:white;font-weight:bold}
small{display:block;text-align:center;color:#8791a4;margin-top:8px}
</style>
</head>
<body>
<header>Oreki <span>San AI</span></header>
<main id="chat">
 <div class="welcome" id="welcome">
  <h1>Welcome AI-KUN 🎀</h1>
  <p>Assalamu alaikum! Main Oreki San hoon. Kya help chahiye?</p>
 </div>
</main>
<div id="bottom">
 <form id="form">
  <textarea id="prompt" rows="1" placeholder="Message Oreki San..." required></textarea>
  <button id="send">Send</button>
 </form>
 <small>AI kabhi galat jawab de sakta hai—zaroori baat verify kar lena.</small>
</div>
<script>
const chat=document.getElementById("chat");
const form=document.getElementById("form");
const input=document.getElementById("prompt");
const send=document.getElementById("send");
let history=[];

function add(text,who){
 document.getElementById("welcome")?.remove();
 const div=document.createElement("div");
 div.className="msg "+who;
 div.textContent=text;
 chat.appendChild(div);
 window.scrollTo(0,document.body.scrollHeight);
 return div;
}
input.addEventListener("keydown",e=>{
 if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();form.requestSubmit();}
});
form.addEventListener("submit",async e=>{
 e.preventDefault();
 const message=input.value.trim();
 if(!message)return;
 add(message,"user");
 input.value="";
 history.push({role:"user",content:message});
 send.disabled=true;
 const waiting=add("Soch raha hoon...","ai");
 try{
  const res=await fetch("/chat",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify({message,history})
  });
  const data=await res.json();
  if(!res.ok)throw new Error(data.error||"Request failed");
  waiting.textContent=data.reply;
  history.push({role:"assistant",content:data.reply});
 }catch(err){
  waiting.textContent="Error: "+err.message;
 }finally{
  send.disabled=false;
  input.focus();
 }
});
</script>
</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
    def send_data(self, status, data, content_type):
        body = data.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_data(200, HTML, "text/html; charset=utf-8")
        else:
            self.send_data(404, "Not found", "text/plain")

    def do_POST(self):
        if self.path != "/chat":
            self.send_data(404, '{"error":"Not found"}', "application/json")
            return

        if not API_KEY:
            self.send_data(
                500,
                json.dumps({"error":"Server mein OPENAI_API_KEY secret set nahi hai."}),
                "application/json"
            )
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            message = str(body.get("message", "")).strip()
            history = body.get("history", [])

            if not message:
                self.send_data(400, '{"error":"Message likho."}', "application/json")
                return

            input_messages = []
            if isinstance(history, list):
                for item in history[-12:]:
                    if isinstance(item, dict) and item.get("role") in ("user", "assistant"):
                        content = item.get("content")
                        if isinstance(content, str):
                            input_messages.append({
                                "role": item["role"],
                                "content": content[:6000]
                            })

            # Latest user message is already included in browser history.
            if not input_messages or input_messages[-1]["content"] != message:
                input_messages.append({"role":"user","content":message})

            payload = {
                "model": MODEL,
                "instructions": (
                    "You are Oreki San, a friendly and helpful AI assistant. "
                    "Start a new conversation with 'Welcome AI-KUN 🎀' when appropriate. "
                    "Reply in the language the user uses, including Hindi and Hinglish. "
                    "Help with everyday questions, study, math, science, coding, writing, "
                    "and jokes. Be accurate, explain clearly, and admit uncertainty. "
                    "Do not claim to create images or browse the web unless those tools "
                    "are actually available."
                ),
                "input": input_messages
            }

            req = urllib.request.Request(
                "https://api.openai.com/v1/responses",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": "Bearer " + API_KEY,
                    "Content-Type": "application/json"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))

            answer = result.get("output_text", "")
            if not answer:
                parts = []
                for item in result.get("output", []):
                    for content in item.get("content", []):
                        if content.get("type") == "output_text":
                            parts.append(content.get("text", ""))
                answer = "\n".join(parts).strip()

            self.send_data(
                200,
                json.dumps({"reply": answer or "Reply nahi mila."}),
                "application/json"
            )

        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            self.send_data(
                502,
                json.dumps({"error":"OpenAI API error: " + detail[:500]}),
                "application/json"
            )
        except Exception as error:
            self.send_data(
                500,
                json.dumps({"error":"Server error: " + str(error)}),
                "application/json"
            )

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print("Oreki San is running on port", PORT)
    server.serve_forever()
