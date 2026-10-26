from pathlib import Path
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)


ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "video"
REPORT_DIR = ROOT / "report"
TMP = ROOT / ".build"
VIDEO_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)
TMP.mkdir(exist_ok=True)

FONT_PATH = Path("/System/Library/Fonts/AppleSDGothicNeo.ttc")
ROLLOUTS = [
    ROOT / "assets" / "baseline_rollouts" / "rollout_ep0.mp4",
    ROOT / "assets" / "baseline_rollouts" / "rollout_ep1.mp4",
    ROOT / "assets" / "baseline_rollouts" / "rollout_ep2.mp4",
]
for path in ROLLOUTS:
    if not path.is_file():
        raise FileNotFoundError(path)


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def slide(name: str, title: str, body: str, accent=(80, 212, 170)) -> Path:
    path = TMP / f"{name}.png"
    im = Image.new("RGB", (1920, 1080), (13, 21, 34))
    draw = ImageDraw.Draw(im)
    title_font = ImageFont.truetype(str(FONT_PATH), 74)
    body_font = ImageFont.truetype(str(FONT_PATH), 42)
    small_font = ImageFont.truetype(str(FONT_PATH), 28)
    draw.rectangle((0, 0, 1920, 18), fill=accent)
    draw.text((130, 155), title, font=title_font, fill=(246, 249, 252))
    y = 320
    for para in body.split("\n"):
        for line in textwrap.wrap(para, width=35) or [""]:
            draw.text((135, y), line, font=body_font, fill=(205, 216, 229))
            y += 62
        y += 18
    draw.text((135, 990), "Physical AI応用1 最終課題 / Kamamoto", font=small_font, fill=(118, 137, 158))
    im.save(path)
    return path


slides = [
    slide("01", "SmolVLAの主要機構実装", "画像・言語・ロボット状態から\nAction chunkを生成するVLAをPyTorchで実装"),
    slide("02", "タスク", "LIBERO-Spatial環境で、\n黒いボウルをつかみプレートへ置く\nロボット操作を学習・評価"),
    slide("03", "ベースラインの成功例", "以下はLIBERO-Spatialで得られた\n事前学習済みポリシーのロールアウト例\n自作300-stepモデルとは別結果"),
    slide("04", "自作したAIポリシー", "SmolVLM2-500M（凍結）\n＋ ロボット状態投影\n＋ Flow Matching Transformer\n＋ 8-step Action chunk"),
    slide("05", "結果と考察", "10タスク×5エピソード / 300 steps\n最終loss: 0.5915 / 評価: 0/2成功\n\n学翑量とAction head容量の不足を確認"),
    slide("06", "次の改善", "学翑ステップとデータを増やす\n複数カメラとより長いAction chunkを比較\n失敗軌道を分析して重点学翑"),
]

segments = []
for i, (img, duration) in enumerate(zip(slides[:3], [8, 9, 7]), 1):
    out = TMP / f"slide_{i}.mp4"
    run("ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-loop", "1", "-i", str(img), "-t", str(duration), "-r", "30", "-vf", "format=yuv420p", str(out))
    segments.append(out)

for i, source in enumerate(ROLLOUTS):
    out = TMP / f"rollout_{i}.mp4"
    vf = (
        "setpts=2.0*PTS,scale=1080:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0d1522"
    )
    run("ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source), "-vf", vf, "-r", "30", "-an", str(out))
    segments.append(out)

for i, (img, duration) in enumerate(zip(slides[3:], [11, 12, 10]), 4):
    out = TMP / f"slide_{i}.mp4"
    run("ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-loop", "1", "-i", str(img), "-t", str(duration), "-r", "30", "-vf", "format=yuv420p", str(out))
    segments.append(out)

concat = TMP / "concat.txt"
concat.write_text("".join(f"file '{p}'\n" for p in segments), encoding="utf-8")
video_path = VIDEO_DIR / "PAI最終課題_Kamamoto.mp4"
run("ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(video_path))


pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
JP_FONT = "HeiseiKakuGo-W5"
PAGE_W, PAGE_H = A4
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="JPTitle", fontName=JP_FONT, fontSize=25, leading=33, textColor=colors.HexColor("#132238"), alignment=TA_LEFT, spaceAfter=12, wordWrap="CJK"))
styles.add(ParagraphStyle(name="JPSub", fontName=JP_FONT, fontSize=13, leading=20, textColor=colors.HexColor("#3A536F"), spaceAfter=10, wordWrap="CJK"))
styles.add(ParagraphStyle(name="JPH1", fontName=JP_FONT, fontSize=16, leading=23, textColor=colors.HexColor("#0C7C6E"), spaceBefore=9, spaceAfter=7, wordWrap="CJK"))
styles.add(ParagraphStyle(name="JPBody", fontName=JP_FONT, fontSize=10.2, leading=16.5, textColor=colors.HexColor("#203040"), spaceAfter=6, wordWrap="CJK"))
styles.add(ParagraphStyle(name="JPSmall", fontName=JP_FONT, fontSize=8.5, leading=13, textColor=colors.HexColor("#53677C"), wordWrap="CJK"))
styles.add(ParagraphStyle(name="JPCenter", fontName=JP_FONT, fontSize=11, leading=17, alignment=TA_CENTER, textColor=colors.HexColor("#203040"), wordWrap="CJK"))


def page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#0C7C6E"))
    canvas.rect(0, PAGE_H - 7 * mm, PAGE_W, 7 * mm, fill=1, stroke=0)
    canvas.setFont(JP_FONT, 8)
    canvas.setFillColor(colors.HexColor("#607487"))
    canvas.drawString(18 * mm, 11 * mm, "Physical AI応用1 最終課題")
    canvas.drawRightString(PAGE_W - 18 * mm, 11 * mm, str(doc.page))
    canvas.restoreState()


doc_path = REPORT_DIR / "説明資料_PAI最終課題_Kamamoto.pdf"
doc = BaseDocTemplate(str(doc_path), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
doc.addPageTemplates(PageTemplate(id="all", frames=frame, onPage=page))


def P(text, style="JPBody"):
    return Paragraph(text, styles[style])


story = [
    Spacer(1, 18*mm),
    P("SmolVLAの主要機構実装と<br/>LIBEROロボット操作", "JPTitle"),
    P("Physical AI応用1講座 最終課題", "JPSub"),
    Spacer(1, 6*mm),
    Table([[P("作品概要", "JPCenter"), P("画像・言語・ロボット状態から、8ステップの操作量を生成するVision-Language-ActionモデルをPyTorchで実装し、LIBERO-plusで学習と評価を行った。")], [P("対象タスク", "JPCenter"), P("LIBERO-Spatial: 黒いボウルをつかみ、プレート上へ置く操作。初期配置の異なる10タスクを使用した。")]], colWidths=[35*mm, 135*mm], style=TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#E8F4F1")),("BOX",(0,0),(-1,-1),0.6,colors.HexColor("#9CB8B2")),("INNERGRID",(0,0),(-1,-1),0.3,colors.HexColor("#C2D3D0")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)])),
    Spacer(1, 8*mm),
    P("1. 目的", "JPH1"),
    P("完成済みモデルを呼び出すだけではなく、VLAの学翑原理をコードレベルで理解することを目的とした。特にFlow Matching、時刻埋め込み、画像・言語・状態の統合、Action chunking、Euler積分を一連のポリシーとして実装した。"),
    P("2. システム構成", "JPH1"),
    Table([[P("観測", "JPCenter"), P("前方カメラ画像 + 自然言語指示 + 8次元ロボット状態")], [P("特徴抽出", "JPCenter"), P("SmolVLM2-500M-Video-Instruct（学翑中は凍結）")], [P("操作生成", "JPCenter"), P("4層Flow Matching Transformer、hidden dim 256")], [P("出力", "JPCenter"), P("7次元action × 8-step chunk")]], colWidths=[35*mm, 135*mm], style=TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#E8F4F1")),("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#B3C8C4")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)])),
    PageBreak(),
    P("3. 学習と推論の工夫", "JPH1"),
    P("学習時は教師action <i>a</i>と正規ノイズ <i>x</i><sub>0</sub>の間を <i>x</i><sub>t</sub>=(1-t)<i>x</i><sub>0</sub>+t<i>a</i> で補間し、目標速度 <i>v</i>*=<i>a</i>-<i>x</i><sub>0</sub> を予測した。推論時はノイズから開始し、10回のEuler更新でactionを復元した。"),
    P("工夫点は、画像と言語だけでなく現在のロボット状態を1つのトークンとして統合したこと、操作次元ごとのスケール差を抑えるためactionを正規化したこと、連続する8操作をまとめて生成したことである。"),
    P("4. 使用データと学習条件", "JPH1"),
    Table([[P("項目", "JPCenter"), P("設定", "JPCenter")], [P("データ"), P("lerobot/libero_plus, revision f3f49f426d75030177b18778374005bc12ccd588")], [P("タスク / episode"), P("LIBERO-Spatial 10タスク / 各5 episode / 合50 episode")], [P("学翑量"), P("300 steps, batch size 1, AdamW")], [P("学翑率"), P("3e-4, warmup 30 steps, cosine decay")], [P("学翑対象"), P("VLMを凍結し、Flow Matching head・VLM projector・state projectorを学翑（4,454,407 parameters）")], [P("実行環境"), P("Tesla T4, PyTorch 2.11.0+cu128, Python 3.13.15")]], colWidths=[40*mm, 130*mm], repeatRows=1, style=TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0C7C6E")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#AABDBA")),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F3F7F6")]),("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)])),
    P("5. 実験結果", "JPH1"),
    P("学翑は300ステップ完了し、最終lossは0.5915となった。自作モデルの評価は2 rollout中0成功（0%）だった。提出動画には環境と目標動作を示すため、別の事前学翑済みポリシーによる成功ロールアウト例も明示的に区別して収録した。"),
    PageBreak(),
    P("6. 考察と試行錯誤", "JPH1"),
    P("失敗の主因は、学翑量の少なさと考えられる。学翑に使用したのは50 episode、300 stepsであり、凍結VLMから得た特徴をロボット操作に対応付けるには不十分だった。また、教材版は4層・hidden dim 256のAction headであり、より大きな公式SmolVLA構成より表現力が限られる。"),
    P("一方、自作した数式部分と学翑パイプラインは最後まで実行でき、動画出力も生成された。これにより、VLAの成否はモデルの機構だけでなく、学翑データ、学翑時間、評価条件の組み合わせで決まることを確認できた。"),
    P("7. 改善案", "JPH1"),
    P("今後は、(1) 学翑ステップとepisode数の増加、(2) 失敗が多い初期配置の重点抽出、(3) frontとwristの複数視点利用、(4) chunk長8/16/32の比較、(5) 事前学翑済みAction headの利用を進める。単発評価の偶然性を減らすため、タスクごとに複数seedで評価する。"),
    P("8. 再現性と提出物", "JPH1"),
    Table([[P("ベースモデル"), P("lerobot/smolvla_libero_plus @ 7bb70aa5bc92b82c9239142775d3a173103567ff")], [P("バックボーン"), P("HuggingFaceTB/SmolVLM2-500M-Video-Instruct")], [P("チェックポイント指紋"), P("SHA-256: 33d9185ff59ded644db54b19c867c0c2c0e72172acce8a19a1a3b84c775188b3")], [P("GitHub"), P("https://github.com/aflat-code/pai-final-smolvla-libero")], [P("YouTube"), P("限定公開または公開URLをOmniCampus提出時に記入")]], colWidths=[45*mm,125*mm], style=TableStyle([("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#B3C8C4")),("BACKGROUND",(0,0),(0,-1),colors.HexColor("#E8F4F1")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)])),
    P("9. 権利関係", "JPH1"),
    P("本実験はLeRobot、SmolVLM2、LIBERO/LIBERO-plus、Hugging Faceの公開モデル・データ・実装を利用した。それぞれの配布元が示すライセンスと利用条件に従う。本提出用リポジトリには大容量の学翑済み重みを含めない。"),
]
doc.build(story)
print(video_path)
print(doc_path)
