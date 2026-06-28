import http.server, socketserver, json, subprocess, threading

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

    def analyze(self, fen, movetime=4000):
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
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent;-webkit-user-select:none;user-select:none}
body{margin:0;background:linear-gradient(160deg,#11131c,#1c2233);color:#e6eaf5;font-family:system-ui,-apple-system,sans-serif;text-align:center}
#wrap{max-width:500px;margin:0 auto;padding:8px}
h2{margin:10px 0 6px;font-size:19px;letter-spacing:1px}
canvas{border-radius:12px;width:100%;height:auto;touch-action:none;box-shadow:0 6px 24px rgba(0,0,0,.5)}
.row{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:8px 0}
button{flex:1;min-width:72px;padding:12px 6px;border:0;border-radius:10px;background:#39456a;color:#fff;font-size:15px;font-weight:600;transition:.1s}
button:active{transform:scale(.96)}
.go{background:linear-gradient(135deg,#e0533d,#c0392b);font-size:16px}
.mv{background:linear-gradient(135deg,#2faa5a,#1e8c47)}
#bar{display:flex;align-items:center;gap:10px;background:#222842;border-radius:10px;padding:10px;margin:8px 0;font-size:14px}
#bar input{flex:1}
#turn{padding:11px;border-radius:10px;font-size:15px;font-weight:600}
.red{background:#5a2330;color:#ff9b9b}.blk{background:#23304a;color:#9bc2ff}
#out{margin:8px 0;padding:14px;background:#222842;border-radius:10px;font-size:16px;min-height:26px;line-height:1.6}
.hint{color:#8a93b0;font-size:13px;margin-top:4px}
b.bm{color:#4ade80;font-size:18px}
</style></head><body><div id="wrap">
<h2>🐟 皮卡鱼象棋助手</h2>
<canvas id="b"></canvas>
<div id="turn" class="red" onclick="toggleTurn()">● 轮到 <span id="tn">红方</span> 走　(点我切换)</div>
<div id="bar">思考 <span id="mtv">4</span> 秒<input id="mt" type="range" min="1" max="20" value="4" oninput="document.getElementById('mtv').textContent=this.value"></div>
<div class="row">
<button class="go" onclick="analyze()">🐟 分析最优</button>
<button class="mv" onclick="playBest()">➡️ 走最优</button>
</div>
<div class="row">
<button onclick="undo()">↶ 撤销</button>
<button onclick="reset()">↺ 重摆开局</button>
<button onclick="flip()">🔄 翻转棋盘</button>
</div>
<div id="out">点棋子选中、再点目标格走子。把局面摆得和实战一模一样,选对「轮到谁」,再点分析。</div>
<div class="hint" id="warn"></div>
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
let turn='w', sel=null, lastMove=null, best=null, bestUci=null, hist=[], flipped=false;
const NAME={k:'将',a:'士',b:'象',n:'馬',r:'車',c:'砲',p:'卒',K:'帥',A:'仕',B:'相',N:'傌',R:'俥',C:'炮',P:'兵'};
const cv=document.getElementById('b'),ctx=cv.getContext('2d');
let W,cell,pad;
function fit(){W=Math.min(window.innerWidth-16,470);cv.width=W*2;cv.height=W*2*10/9;cv.style.width=W+'px';cv.style.height=(W*10/9)+'px';ctx.setTransform(2,0,0,2,0,0);cell=W/9;pad=cell/2;draw();}
function dispToBoard(dr,dc){return flipped?{r:9-dr,c:8-dc}:{r:dr,c:dc};}
function boardToDisp(r,c){return flipped?{dr:9-r,dc:8-c}:{dr:r,dc:c};}
function X(dc){return pad+dc*cell;}
function Y(dr){return pad+dr*cell;}
function draw(){
ctx.clearRect(0,0,W,W*10/9);
let g=ctx.createLinearGradient(0,0,W,W*10/9);g.addColorStop(0,'#f3dcae');g.addColorStop(1,'#e7c88c');
ctx.fillStyle=g;ctx.fillRect(0,0,W,W*10/9);
ctx.strokeStyle='#6b4f29';ctx.lineWidth=1.3;
for(let r=0;r<ROWS;r++){ctx.beginPath();ctx.moveTo(X(0),Y(r));ctx.lineTo(X(8),Y(r));ctx.stroke();}
for(let c=0;c<COLS;c++){
if(c===0||c===8){ctx.beginPath();ctx.moveTo(X(c),Y(0));ctx.lineTo(X(c),Y(9));ctx.stroke();}
else{ctx.beginPath();ctx.moveTo(X(c),Y(0));ctx.lineTo(X(c),Y(4));ctx.stroke();ctx.beginPath();ctx.moveTo(X(c),Y(5));ctx.lineTo(X(c),Y(9));ctx.stroke();}}
ctx.beginPath();ctx.moveTo(X(3),Y(0));ctx.lineTo(X(5),Y(2));ctx.moveTo(X(5),Y(0));ctx.lineTo(X(3),Y(2));
ctx.moveTo(X(3),Y(7));ctx.lineTo(X(5),Y(9));ctx.moveTo(X(5),Y(7));ctx.lineTo(X(3),Y(9));ctx.stroke();
ctx.fillStyle='#8a6a38';ctx.font='italic '+(cell*0.42)+'px serif';ctx.textAlign='center';ctx.textBaseline='middle';
ctx.fillText('楚　河',X(2),Y(4.5));ctx.fillText('漢　界',X(6),Y(4.5));
if(lastMove){let a=boardToDisp(lastMove.fr,lastMove.fc),b=boardToDisp(lastMove.tr,lastMove.tc);hl(a.dr,a.dc,'rgba(80,160,255,.32)');hl(b.dr,b.dc,'rgba(80,160,255,.32)');}
if(best){let a=boardToDisp(best.fr,best.fc),b=boardToDisp(best.tr,best.tc);arrow(a.dr,a.dc,b.dr,b.dc);}
if(sel){let a=boardToDisp(sel.r,sel.c);hl(a.dr,a.dc,'rgba(255,200,0,.55)');}
for(let r=0;r<ROWS;r++)for(let c=0;c<COLS;c++){const p=board[r][c];if(p){let d=boardToDisp(r,c);piece(d.dr,d.dc,p);}}
}
function hl(dr,dc,col){ctx.fillStyle=col;ctx.beginPath();ctx.arc(X(dc),Y(dr),cell*0.46,0,7);ctx.fill();}
function piece(dr,dc,p){
const red=p===p.toUpperCase();const x=X(dc),y=Y(dr),rad=cell*0.43;
ctx.beginPath();ctx.arc(x,y+1.5,rad,0,7);ctx.fillStyle='rgba(0,0,0,.25)';ctx.fill();
let g=ctx.createRadialGradient(x-rad*0.3,y-rad*0.3,rad*0.2,x,y,rad);g.addColorStop(0,'#fffdf6');g.addColorStop(1,'#e8d9b8');
ctx.beginPath();ctx.arc(x,y,rad,0,7);ctx.fillStyle=g;ctx.fill();
ctx.lineWidth=2.2;ctx.strokeStyle=red?'#b3372a':'#2a2a2a';ctx.stroke();
ctx.beginPath();ctx.arc(x,y,rad*0.8,0,7);ctx.lineWidth=1;ctx.stroke();
ctx.fillStyle=red?'#b3372a':'#1a1a1a';ctx.font='bold '+(cell*0.5)+'px "KaiTi","STKaiti",serif';ctx.textAlign='center';ctx.textBaseline='middle';
ctx.fillText(NAME[p],x,y+1);
}
function arrow(fdr,fdc,tdr,tdc){
const fx=X(fdc),fy=Y(fdr),tx=X(tdc),ty=Y(tdr);
ctx.strokeStyle='rgba(34,197,94,.95)';ctx.lineWidth=5;ctx.lineCap='round';ctx.beginPath();ctx.moveTo(fx,fy);ctx.lineTo(tx,ty);ctx.stroke();
const a=Math.atan2(ty-fy,tx-fx);ctx.fillStyle='rgba(34,197,94,.95)';ctx.beginPath();
ctx.moveTo(tx,ty);ctx.lineTo(tx-15*Math.cos(a-0.45),ty-15*Math.sin(a-0.45));ctx.lineTo(tx-15*Math.cos(a+0.45),ty-15*Math.sin(a+0.45));ctx.fill();
}
cv.addEventListener('click',e=>{
const rc=cv.getBoundingClientRect();
const px=(e.clientX-rc.left)/rc.width*W, py=(e.clientY-rc.top)/rc.height*(W*10/9);
let cc=Math.round((px-pad)/cell), rr=Math.round((py-pad)/cell);
if(cc<0||cc>8||rr<0||rr>9)return;
const bp=dispToBoard(rr,cc);
if(sel){
if(sel.r===bp.r&&sel.c===bp.c){sel=null;draw();return;}
hist.push(JSON.stringify(board));
board[bp.r][bp.c]=board[sel.r][sel.c];board[sel.r][sel.c]=0;
lastMove={fr:sel.r,fc:sel.c,tr:bp.r,tc:bp.c};sel=null;best=null;draw();
}else{
if(board[bp.r][bp.c]){sel=bp;draw();}
}
});
function genFEN(){
let f='';
for(let r=0;r<ROWS;r++){let e=0,row='';
for(let c=0;c<COLS;c++){const p=board[r][c];if(p){if(e){row+=e;e=0}row+=p}else e++;}
if(e)row+=e;f+=row;if(r<9)f+='/';}
return f+' '+turn+' - - 0 1';
}
function uci2rc(u){return {fc:u.charCodeAt(0)-97,fr:9-(+u[1]),tc:u.charCodeAt(2)-97,tr:9-(+u[3])};}
function chk(){
let wk=0,bk=0;for(let r=0;r<10;r++)for(let c=0;c<9;c++){if(board[r][c]==='K')wk++;if(board[r][c]==='k')bk++;}
document.getElementById('warn').textContent=(wk===1&&bk===1)?'':'⚠️ 棋盘上必须各有 1 个帅和 1 个将,现在 帅='+wk+' 将='+bk+',局面非法会算不准!';
}
async function analyze(){
chk();best=null;sel=null;draw();
document.getElementById('out').textContent='🐟 皮卡鱼思考中...';
try{
const res=await fetch('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({fen:genFEN(),movetime:(+document.getElementById('mt').value)*1000})});
const d=await res.json();
if(!d.bestmove||d.bestmove==='(none)'){document.getElementById('out').textContent='⚠️ 没算出着法,检查局面/轮到谁是否摆对';return;}
bestUci=d.bestmove;best=uci2rc(d.bestmove);
const fp=board[best.fr][best.fc];const nm=fp?NAME[fp]:'?';
let sc=d.score||'',txt='';
if(sc.startsWith('mate')){const n=sc.split(' ')[1];txt=(+n>0?'🔥 '+Math.abs(n)+' 步绝杀!':'💀 '+Math.abs(n)+'步被杀');}
else if(sc.startsWith('cp')){const v=+sc.split(' ')[1];txt=(v>0?'优势 +':'劣势 ')+v;}
document.getElementById('out').innerHTML='🐟 最优:<b class="bm">'+nm+' '+d.bestmove+'</b><br>'+txt+'<div class="hint">绿箭头就是要走的棋,可点「走最优」自动走</div>';
draw();
}catch(e){document.getElementById('out').textContent='❌ 连服务器失败:'+e;}
}
function playBest(){
if(!best){document.getElementById('out').textContent='先点「分析最优」';return;}
hist.push(JSON.stringify(board));
board[best.tr][best.tc]=board[best.fr][best.fc];board[best.fr][best.fc]=0;
lastMove={fr:best.fr,fc:best.fc,tr:best.tr,tc:best.tc};
best=null;turn=turn==='w'?'b':'w';updTurn();draw();
document.getElementById('out').textContent='✅ 已走最优。换对手走了,对手走完你摆上,再分析。';
}
function updTurn(){const t=document.getElementById('turn');document.getElementById('tn').textContent=turn==='w'?'红方':'黑方';t.className=turn==='w'?'red':'blk';t.firstChild.textContent=turn==='w'?'● 轮到 ':'● 轮到 ';}
function toggleTurn(){turn=turn==='w'?'b':'w';best=null;updTurn();draw();}
function reset(){board=JSON.parse(JSON.stringify(START));turn='w';sel=null;lastMove=null;best=null;hist=[];updTurn();draw();document.getElementById('out').textContent='已摆回开局。';document.getElementById('warn').textContent='';}
function flip(){flipped=!flipped;draw();}
function undo(){if(hist.length){board=JSON.parse(hist.pop());sel=null;best=null;lastMove=null;draw();}}
window.addEventListener('resize',fit);updTurn();fit();
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
                best, score = engine.analyze(data.get("fen", ""), int(data.get("movetime", 4000)))
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
