import http.server, socketserver, json, subprocess, threading, os

ENGINE = "/opt/xq/pikafish"
WD = "/opt/xq"
PORT = 8090

class Engine:
    def __init__(self):
        self.p = subprocess.Popen([ENGINE], cwd=WD, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, bufsize=1)
        self.lock = threading.Lock()
        self._wait("uci", "uciok")
        self._send("setoption name Threads value 4")
        self._send("setoption name Hash value 512")
        self._wait("isready", "readyok")

    def _send(self, c):
        self.p.stdin.write(c + "\n")
        self.p.stdin.flush()

    def _wait(self, cmd, token):
        self._send(cmd)
        while True:
            line = self.p.stdout.readline()
            if not line or line.strip().startswith(token):
                break

    def analyze(self, fen, movetime=3000):
        with self.lock:
            self._send("ucinewgame")
            self._send("position fen " + fen)
            self._send("go movetime %d" % movetime)
            best, score = None, ""
            while True:
                line = self.p.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if line.startswith("info") and " score " in line:
                    parts = line.split()
                    if "score" in parts:
                        i = parts.index("score")
                        score = " ".join(parts[i+1:i+3])
                if line.startswith("bestmove"):
                    best = line.split()[1]
                    break
            return best, score

engine = Engine()

HTML = r'''<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>皮卡鱼象棋助手</title>
<style>
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{margin:0;background:#1a1d29;color:#e0e4f0;font-family:system-ui,sans-serif;text-align:center}
h2{margin:8px;font-size:18px}
#wrap{max-width:480px;margin:0 auto;padding:6px}
canvas{background:#f0d9a8;border-radius:8px;width:100%;height:auto;touch-action:none}
.row{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin:8px 0}
button{flex:1;min-width:70px;padding:10px;border:0;border-radius:8px;background:#3a4668;color:#fff;font-size:15px}
button:active{background:#56689c}
.go{background:#c0392b}.go:active{background:#e74c3c}
#turn{padding:10px;border-radius:8px;background:#2a3048;font-size:15px}
#out{margin:8px;padding:12px;background:#222842;border-radius:8px;font-size:16px;min-height:24px;line-height:1.5}
.hint{color:#8a93b0;font-size:13px}
select{padding:8px;border-radius:8px;background:#2a3048;color:#fff;border:0;font-size:14px}
</style></head><body><div id="wrap">
<h2>♟️ 皮卡鱼象棋助手</h2>
<canvas id="b"></canvas>
<div class="row">
<div id="turn" onclick="toggleTurn()">轮到:<b id="tn">红方</b>(点切换)</div>
<select id="mt"><option value="2000">2秒</option><option value="4000" selected>4秒</option><option value="8000">8秒</option><option value="15000">15秒(最强)</option></select>
</div>
<div class="row">
<button class="go" onclick="analyze()">🐟 让皮卡鱼分析</button>
</div>
<div class="row">
<button onclick="reset()">↺ 摆回开局</button>
<button onclick="clearBoard()">空盘自摆</button>
<button onclick="undo()">↶ 撤销</button>
</div>
<div id="out">点棋子选中、再点目标格走子。对手走一步你也走一步,然后点「让皮卡鱼分析」。</div>
<div class="hint">红方在下、黑方在上。摆成和实战一样的局面,选好「轮到谁」,再分析。</div>
</div>
<script>
const COLS=9,ROWS=10;
const START=[
['r','n','b','a','k','a','b','n','r'],
[0,0,0,0,0,0,0,0,0],
[0,'c',0,0,0,0,0,'c',0],
['p',0,'p',0,'p',0,'p',0,'p'],
[0,0,0,0,0,0,0,0,0],
[0,0,0,0,0,0,0,0,0],
['P',0,'P',0,'P',0,'P',0,'P'],
[0,'C',0,0,0,0,0,'C',0],
[0,0,0,0,0,0,0,0,0],
['R','N','B','A','K','A','B','N','R']];
let board=JSON.parse(JSON.stringify(START));
let turn='w', sel=null, lastMove=null, best=null, hist=[];
const NAME={k:'将',a:'士',b:'象',n:'馬',r:'車',c:'砲',p:'卒',K:'帥',A:'仕',B:'相',N:'马',R:'车',C:'炮',P:'兵'};
const cv=document.getElementById('b'),ctx=cv.getContext('2d');
let W,cell,pad;
function fit(){W=Math.min(window.innerWidth-12,460);cv.width=W;cell=W/9;pad=cell/2;cv.height=cell*10;draw();}
function X(c){return pad+c*cell;}
function Y(r){return pad+r*cell;}
function draw(){
ctx.clearRect(0,0,cv.width,cv.height);
ctx.fillStyle='#f0d9a8';ctx.fillRect(0,0,cv.width,cv.height);
ctx.strokeStyle='#7a5c2e';ctx.lineWidth=1.4;
for(let r=0;r<ROWS;r++){ctx.beginPath();ctx.moveTo(X(0),Y(r));ctx.lineTo(X(8),Y(r));ctx.stroke();}
for(let c=0;c<COLS;c++){
if(c===0||c===8){ctx.beginPath();ctx.moveTo(X(c),Y(0));ctx.lineTo(X(c),Y(9));ctx.stroke();}
else{ctx.beginPath();ctx.moveTo(X(c),Y(0));ctx.lineTo(X(c),Y(4));ctx.stroke();ctx.beginPath();ctx.moveTo(X(c),Y(5));ctx.lineTo(X(c),Y(9));ctx.stroke();}}
ctx.beginPath();ctx.moveTo(X(3),Y(0));ctx.lineTo(X(5),Y(2));ctx.moveTo(X(5),Y(0));ctx.lineTo(X(3),Y(2));
ctx.moveTo(X(3),Y(7));ctx.lineTo(X(5),Y(9));ctx.moveTo(X(5),Y(7));ctx.lineTo(X(3),Y(9));ctx.stroke();
if(lastMove){hl(lastMove.fr,lastMove.fc,'rgba(80,160,255,.35)');hl(lastMove.tr,lastMove.tc,'rgba(80,160,255,.35)');}
if(best){arrow(best);}
if(sel){hl(sel.r,sel.c,'rgba(255,210,0,.5)');}
for(let r=0;r<ROWS;r++)for(let c=0;c<COLS;c++){const p=board[r][c];if(p)piece(r,c,p);}
}
function hl(r,c,col){ctx.fillStyle=col;ctx.beginPath();ctx.arc(X(c),Y(r),cell*0.46,0,7);ctx.fill();}
function piece(r,c,p){
const red=p===p.toUpperCase();
ctx.beginPath();ctx.arc(X(c),Y(r),cell*0.42,0,7);
ctx.fillStyle='#f7eeda';ctx.fill();ctx.lineWidth=2;ctx.strokeStyle=red?'#c0392b':'#222';ctx.stroke();
ctx.fillStyle=red?'#c0392b':'#222';ctx.font='bold '+(cell*0.52)+'px serif';ctx.textAlign='center';ctx.textBaseline='middle';
ctx.fillText(NAME[p],X(c),Y(r)+1);
}
function arrow(m){
const fx=X(m.fc),fy=Y(m.fr),tx=X(m.tc),ty=Y(m.tr);
ctx.strokeStyle='rgba(0,180,80,.9)';ctx.lineWidth=4;ctx.beginPath();ctx.moveTo(fx,fy);ctx.lineTo(tx,ty);ctx.stroke();
const a=Math.atan2(ty-fy,tx-fx);ctx.fillStyle='rgba(0,180,80,.9)';ctx.beginPath();
ctx.moveTo(tx,ty);ctx.lineTo(tx-12*Math.cos(a-0.4),ty-12*Math.sin(a-0.4));ctx.lineTo(tx-12*Math.cos(a+0.4),ty-12*Math.sin(a+0.4));ctx.fill();
}
cv.addEventListener('click',e=>{
const rc=cv.getBoundingClientRect(),sx=cv.width/rc.width;
const px=(e.clientX-rc.left)*sx,py=(e.clientY-rc.top)*sx;
let c=Math.round((px-pad)/cell),r=Math.round((py-pad)/cell);
if(c<0||c>8||r<0||r>9)return;
if(sel){
if(sel.r===r&&sel.c===c){sel=null;draw();return;}
hist.push(JSON.stringify(board));
board[r][c]=board[sel.r][sel.c];board[sel.r][sel.c]=0;
lastMove={fr:sel.r,fc:sel.c,tr:r,tc:c};sel=null;best=null;draw();
}else{
if(board[r][c]){sel={r,c};draw();}
}
});
function genFEN(){
let f='';
for(let r=0;r<ROWS;r++){let e=0,row='';
for(let c=0;c<COLS;c++){const p=board[r][c];if(p){if(e){row+=e;e=0}row+=p}else e++;}
if(e)row+=e;f+=row;if(r<9)f+='/';}
return f+' '+turn+' - - 0 1';
}
function uci2rc(u){
return {fc:u.charCodeAt(0)-97,fr:9-(+u[1]),tc:u.charCodeAt(2)-97,tr:9-(+u[3])};
}
function colName(c,red){return red?['九','八','七','六','五','四','三','二','一'][c]:(c+1);}
async function analyze(){
best=null;sel=null;draw();
document.getElementById('out').textContent='🐟 皮卡鱼思考中...';
try{
const res=await fetch('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({fen:genFEN(),movetime:+document.getElementById('mt').value})});
const d=await res.json();
if(!d.bestmove||d.bestmove==='(none)'){document.getElementById('out').textContent='⚠️ 没算出着法,检查局面/轮到谁是否摆对';return;}
best=uci2rc(d.bestmove);
const fp=board[best.fr][best.fc];const nm=fp?NAME[fp]:'';
let sc=d.score||'';
let txt='';
if(sc.startsWith('mate')){const n=sc.split(' ')[1];txt=' (绝杀 '+Math.abs(n)+' 步!)';}
else if(sc.startsWith('cp')){const v=+sc.split(' ')[1];txt=' (优势分:'+(v>0?'+':'')+v+')';}
document.getElementById('out').innerHTML='🐟 <b>最优着法:'+nm+' '+d.bestmove+'</b>'+txt+'<br><span class="hint">绿箭头就是要走的棋,照着在游戏里走</span>';
draw();
}catch(e){document.getElementById('out').textContent='❌ 连接服务器失败:'+e;}
}
function toggleTurn(){turn=turn==='w'?'b':'w';document.getElementById('tn').textContent=turn==='w'?'红方':'黑方';best=null;draw();}
function reset(){board=JSON.parse(JSON.stringify(START));turn='w';document.getElementById('tn').textContent='红方';sel=null;lastMove=null;best=null;hist=[];draw();document.getElementById('out').textContent='已摆回开局。';}
function clearBoard(){board=Array.from({length:10},()=>Array(9).fill(0));sel=null;lastMove=null;best=null;hist=[];draw();document.getElementById('out').textContent='空盘。点格子放...(暂不支持放子,自摆功能下版加,先用开局微调)';}
function undo(){if(hist.length){board=JSON.parse(hist.pop());sel=null;best=null;lastMove=null;draw();}}
window.addEventListener('resize',fit);fit();
</script></body></html>'''

class H(http.server.BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self._send(200, HTML.encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._send(404, b"404", "text/plain")

    def do_POST(self):
        if self.path == "/analyze":
            n = int(self.headers.get("Content-Length", 0))
            try:
                data = json.loads(self.rfile.read(n) or b"{}")
                best, score = engine.analyze(data.get("fen", ""), int(data.get("movetime", 3000)))
                out = json.dumps({"bestmove": best, "score": score}).encode()
            except Exception as e:
                out = json.dumps({"bestmove": None, "score": "", "err": str(e)}).encode()
            self._send(200, out, "application/json")
        else:
            self._send(404, b"404", "text/plain")

    def log_message(self, *a):
        pass

class TS(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

print("皮卡鱼象棋助手已启动,访问 http://<服务器IP>:%d" % PORT)
TS(("0.0.0.0", PORT), H).serve_forever()
