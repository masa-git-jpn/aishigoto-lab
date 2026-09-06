"""
検証用のダミーPDFを作るスクリプト。

- 中身は無意味なテキストのみ（機密情報は一切含まない）
- 圧縮をかけず（pageCompression=0）、ファイルの生バイト列に文字列がそのまま残るようにしてある。
  これにより「送信されたバイト列にファイルの中身が含まれているか」を、
  base64にせずファイルサイズと生バイトの一致だけで確認できる。
- ファイルサイズは2895バイト（今回の検証で「送信された/されなかった」を判定する基準値）

再現方法:
    pip install reportlab
    python3 make_dummy_pdf.py
"""

from reportlab.pdfgen import canvas

def make_pdf(path: str, marker: str) -> None:
    c = canvas.Canvas(path, pageCompression=0)
    c.setFont('Helvetica', 20)
    c.drawString(100, 700, marker)
    c.setFont('Helvetica', 12)
    for i in range(20):
        c.drawString(100, 650 - i * 20, f'dummy line {i + 1} for network verification test')
    c.save()

if __name__ == '__main__':
    make_pdf('dummy_test.pdf', 'AISHIGOTO-LAB-TEST-8823-NETLOG')
    make_pdf('dummy_test2.pdf', 'AISHIGOTO-LAB-TEST-8823-NETLOG')
