"""PTIT PROCON 2026 — Trình thực thi thi đấu và xem kết quả trực tiếp trên Web.

Cách dùng nhanh:
1. Chạy tương tác (tự chọn trận):
   python run_match.py

2. Chạy với ID trận cụ thể:
   python run_match.py -m m-32743

3. Chạy với ID trận và token riêng:
   python run_match.py -m m-32742 -t m-32742-a-b32726021325

4. Chạy thử với Mock Server nội bộ:
   python run_match.py --mock
"""
import argparse
import logging
import os
from pathlib import Path
import sys
import time
import webbrowser

# Đảm bảo UTF-8 trên Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Thêm thư mục gốc vào path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Nạp file .env nếu có
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from client.http_client import ProconHttpClient
from client.mock_server import MockProconServer
from client.runner import MatchRunner
from env.hex_grid import HexGrid
from strategy.hybrid import HybridMARLDPStrategy

# Danh bạ các token đã biết từ hồ sơ đội Mer (PTIT_PROCON_2026_extracted.md)
KNOWN_MATCH_TOKENS = {
    "m-32743": "m-32743-a-40a5bb67eff9",   # Trận luyện tập với máy
    "m-32742": "m-32742-a-b32726021325",   # Trận kiểm tra bot trước trận
    "m-1531":  "m-1531-a-9db1bbd1b61a",
    "m-0959":  "m-0959-a-e653d38ad213",
}

DEFAULT_TEAM_TOKEN = "bot-34d7632cb475ab0680eac8"
DEFAULT_BASE_URL = "https://procon.ptit.edu.vn"


def print_banner():
    banner = r"""
========================================================================================
   ____  ____  ____  ____  ____  ____       ____  ____        __  __ 
  / __ \/ __ \/ __ \/ __ \/ __ \/ __ \     / __ \/ __ \      / / / / 
 / /_/ / /_/ / /_/ / /_/ / /_/ / /_/ /    / / / / /_/ /_____/ /_/ /  
/ ____/ _, _/ ____/ ____/ _, _/ ____/    / /_/ / ____/_____/ __  /   
\/   /_/ |_|\____/\____/_/ |_|\____/____/_____/_/         /_/ /_/    
                                  /_____/                            
  PTIT PROCON 2026 — ĐỘI MER (TRÌNH THỰC THI & THEO DÕI TRẬN ĐẤU)
========================================================================================
"""
    print(banner)


def get_web_match_urls(base_url: str, match_id: str) -> list:
    """Trả về các link web để người dùng xem trận đấu trên trình duyệt."""
    clean_base = base_url.rstrip("/")
    return [
        f"{clean_base}/match/{match_id}",
        f"{clean_base}/matches/{match_id}",
    ]


def interactive_select_match() -> tuple:
    """Hỏi người dùng lựa chọn trận đấu nếu không truyền đối số command line."""
    print("📋 DANH SÁCH CÁC TRẬN ĐẤU CỦA ĐỘI MER:")
    print("  [1] m-32743 (Trận luyện tập với máy: 8x8, 4 ngày, 30 bước/ngày)")
    print("  [2] m-32742 (Trận kiểm tra bot trước trận)")
    print("  [3] Nhập ID trận mới tùy ý...")
    print("  [4] Chạy thử với Mock Server nội bộ (Offline Test)")
    
    choice = input("\n👉 Chọn (1-4 hoặc nhập trực tiếp Match ID, mặc định [1]): ").strip()
    
    if choice == "1" or choice == "":
        match_id = "m-32743"
        token = KNOWN_MATCH_TOKENS["m-32743"]
        use_mock = False
    elif choice == "2":
        match_id = "m-32742"
        token = KNOWN_MATCH_TOKENS["m-32742"]
        use_mock = False
    elif choice == "4":
        match_id = "mock_practice_001"
        token = "mock_token"
        use_mock = True
    else:
        # Nhập Match ID tùy ý
        match_id = choice.replace("3", "").strip() if choice.startswith("3") and len(choice) > 1 else choice
        if not match_id or match_id == "3":
            match_id = input("👉 Nhập Match ID (ví dụ: m-32743): ").strip()
        
        # Tra cứu token
        if match_id in KNOWN_MATCH_TOKENS:
            token = KNOWN_MATCH_TOKENS[match_id]
            print(f"[*] Tìm thấy token có sẵn cho trận {match_id}: {token[:12]}...")
        else:
            custom_token = input(f"👉 Nhập Token cho trận {match_id} (nhấn Enter để dùng Team Token mặc định): ").strip()
            token = custom_token if custom_token else DEFAULT_TEAM_TOKEN
        use_mock = False

    return match_id, token, use_mock


def play_match(
    match_id: str,
    token: str,
    base_url: str = DEFAULT_BASE_URL,
    use_mock: bool = False,
    open_browser: bool = True,
    poll_interval: float = 0.5,
):
    print_banner()

    mock_server = None
    if use_mock:
        mock_server = MockProconServer(total_days=3, start_425_count=1)
        base_url = mock_server.start()
        print(f"[*] Đã khởi chạy Mock Server cục bộ tại: {base_url}")

    web_urls = get_web_match_urls(base_url, match_id)

    print("========================================================================================")
    print(f"  THÔNG TIN KẾT NỐI TRẬN ĐẤU:")
    print(f"  - Server URL : {base_url}")
    print(f"  - Match ID   : {match_id}")
    print(f"  - Token      : {token[:16]}... (đã ẩn một phần vì bảo mật)")
    print(f"  - Chế độ     : {'Mô phỏng (Mock Server)' if use_mock else 'Server Thật (Live Server)'}")
    print("----------------------------------------------------------------------------------------")
    print(f"  🌐 XEM TRẬN ĐẤU TRỰC TIẾP TRÊN WEB:")
    for i, url in enumerate(web_urls, 1):
        print(f"     Link {i}: {url}")
    print("========================================================================================\n")

    # Tự động mở link trận đấu trên trình duyệt nếu không phải mock
    if open_browser and not use_mock:
        try:
            print(f"[*] Đang tự động mở trình duyệt tới: {web_urls[0]}")
            webbrowser.open(web_urls[0])
        except Exception as e:
            print(f"[!] Không thể tự mở trình duyệt ({e}), bạn có thể mở thủ công theo link trên.")

    # Khởi tạo HTTP Client
    client = ProconHttpClient(
        base_url=base_url,
        match_id=match_id,
        token=token,
        min_poll_interval=poll_interval,
    )

    # Khởi tạo Match Runner với HybridMARLDPStrategy và cơ chế cứu hộ tiếp tế
    runner = MatchRunner(
        client=client,
        strategy=None,  # Tự động khởi tạo HybridMARLDPStrategy chuẩn theo setup bản đồ
        poll_interval=poll_interval,
        max_planning_time_ms=950.0,
        log_dir="logs/matches",
    )

    try:
        print("\n🚀 BẮT ĐẦU CHẠY BOT VÀ ĐỒNG BỘ TRẬN ĐẤU...")
        start_time = time.time()
        summary = runner.run()
        total_time = time.time() - start_time

        print("\n" + "=" * 80)
        print("🎉 TRẬN ĐẤU ĐÃ KẾT THÚC THÀNH CÔNG!")
        print("=" * 80)
        print(f"  - Match ID           : {summary.get('match_id')}")
        print(f"  - Số ngày đã đấu     : {summary.get('days_played')}")
        print(f"  - Thời gian diễn ra  : {total_time:.2f} giây")
        print(f"  - Đội thắng (Winner) : {summary.get('winner', 'Chưa công bố')}")
        print(f"  - Điểm số (Scores)   : {summary.get('scores', 'N/A')}")
        print(f"  - File nhật ký trận  : {summary.get('log_file')}")
        print("----------------------------------------------------------------------------------------")
        print(f"  👉 Xem lại đồ họa diễn biến trận đấu tại: {web_urls[0]}")
        print("=" * 80 + "\n")

    except KeyboardInterrupt:
        print("\n[!] Người dùng đã hủy thực thi bot.")
    except Exception as e:
        print(f"\n❌ LỖI TRONG QUÁ TRÌNH KẾT NỐI HOẶC THI ĐẤU: {e}")
        print("💡 Gợi ý xử lý:")
        print("   1. Kiểm tra xem Token và Match ID đã chính xác với trang thi đấu chưa.")
        print("   2. Kiểm tra kết nối mạng hoặc thử chạy offline với cờ --mock để kiểm tra thuật toán.")
    finally:
        if mock_server:
            mock_server.stop()
            print("[*] Đã đóng Mock Server.")


def main():
    parser = argparse.ArgumentParser(
        description="PTIT PROCON 2026 — Trình thực thi thi đấu và xem kết quả trên Web",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-m", "--match",
        type=str,
        default=None,
        help="ID trận đấu (ví dụ: m-32743, m-32742)",
    )
    parser.add_argument(
        "-t", "--token",
        type=str,
        default=None,
        help="Token của trận đấu hoặc của đội (nếu để trống sẽ tự lấy từ hồ sơ đội)",
    )
    parser.add_argument(
        "-u", "--url",
        type=str,
        default=os.getenv("PROCON_BASE_URL", DEFAULT_BASE_URL),
        help=f"URL server PROCON (mặc định: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Chạy với Mock Server nội bộ để kiểm tra thử",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Không tự động mở trình duyệt web khi trận bắt đầu",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=float(os.getenv("PROCON_POLL_INTERVAL", 0.5)),
        help="Khoảng cách giữa các lần thăm dò server (giây, mặc định: 0.5)",
    )

    args = parser.parse_args()

    # Nếu không truyền match id qua CLI, hiển thị menu tương tác
    if args.match is None and not args.mock:
        match_id, token, use_mock = interactive_select_match()
    else:
        match_id = args.match or ("mock_match_001" if args.mock else os.getenv("PROCON_MATCH_ID", "m-32743"))
        if args.token:
            token = args.token
        elif match_id in KNOWN_MATCH_TOKENS:
            token = KNOWN_MATCH_TOKENS[match_id]
        else:
            token = os.getenv("PROCON_TOKEN", DEFAULT_TEAM_TOKEN)
        use_mock = args.mock

    play_match(
        match_id=match_id,
        token=token,
        base_url=args.url,
        use_mock=use_mock,
        open_browser=not args.no_browser,
        poll_interval=args.poll,
    )


if __name__ == "__main__":
    main()
