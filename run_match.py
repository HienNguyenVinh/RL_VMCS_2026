"""PTIT PROCON 2026 — Trình thực thi thi đấu và đồng bộ trận đấu.

Cách dùng đơn giản:
1. Chạy với ID trận tạo trên Web:
   python run_match.py -m m-32744

2. Hoặc chạy không đối số (chỉ cần nhập ID trận):
   python run_match.py

3. Chạy thử nghiệm giả lập offline (Mock Server):
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

# Nạp cấu hình từ file .env nếu có
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from client.http_client import ProconHttpClient
from client.mock_server import MockProconServer
from client.protocol import ProconAuthError
from client.runner import MatchRunner
from env.hex_grid import HexGrid
from strategy.hybrid import HybridMARLDPStrategy

# Token bot mặc định của đội
DEFAULT_BOT_TOKEN = "bot-34d7632cb475a0b0608aeca8"
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
  PTIT PROCON 2026 — ĐỘI MER (TRÌNH THỰC THI & ĐỒNG BỘ THI ĐẤU)
========================================================================================
"""
    print(banner)


def get_web_match_url(base_url: str, match_id: str) -> str:
    """Trả về link web để người dùng tự xem trận đấu trên trình duyệt."""
    clean_base = base_url.rstrip("/")
    return f"{clean_base}/match/{match_id}"


def resolve_token(match_id: str, cli_token: str = None) -> str:
    """Xác định token hợp lệ cho trận đấu."""
    if match_id.startswith("mock"):
        return "mock_token"

    # 1. Ưu tiên cờ CLI nếu có truyền
    if cli_token and cli_token.strip():
        return cli_token.strip()

    # 2. Lấy từ biến môi trường .env (PROCON_TOKEN hoặc PROCON_TEAM_TOKEN)
    env_token = os.getenv("PROCON_TOKEN") or os.getenv("PROCON_TEAM_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()

    # 3. Sử dụng token bot mặc định của đội
    return DEFAULT_BOT_TOKEN


def play_match(
    match_id: str,
    token: str,
    base_url: str = DEFAULT_BASE_URL,
    use_mock: bool = False,
    open_browser: bool = False,
    poll_interval: float = 0.5,
):
    print_banner()

    mock_server = None
    if use_mock:
        mock_server = MockProconServer(total_days=3, start_425_count=1)
        base_url = mock_server.start()
        print(f"[*] Đã khởi chạy Mock Server cục bộ tại: {base_url}")

    web_url = get_web_match_url(base_url, match_id)

    print("========================================================================================")
    print(f"  THÔNG TIN KẾT NỐI:")
    print(f"  - Server URL : {base_url}")
    print(f"  - Match ID   : {match_id}")
    print(f"  - Token      : {token[:12]}... (đã ẩn một phần)")
    print(f"  - Chế độ     : {'Mô phỏng (Mock Server)' if use_mock else 'Server Thật (Live Server)'}")
    print("----------------------------------------------------------------------------------------")
    print(f"  🌐 LINK XEM TRỰC TIẾP TRẬN ĐẤU TRÊN WEB:")
    print(f"     👉 {web_url}")
    print("========================================================================================\n")

    # Mở trình duyệt nếu người dùng bật cờ --open-browser
    if open_browser and not use_mock:
        try:
            print(f"[*] Đang mở trình duyệt tới: {web_url}")
            webbrowser.open(web_url)
        except Exception as e:
            print(f"[!] Không thể mở trình duyệt ({e}), bạn hãy mở link trên.")

    # Khởi tạo HTTP Client
    client = ProconHttpClient(
        base_url=base_url,
        match_id=match_id,
        token=token,
        min_poll_interval=poll_interval,
    )

    # Khởi tạo Match Runner
    runner = MatchRunner(
        client=client,
        strategy=None,  # Tự động khởi tạo HybridMARLDPStrategy theo setup bản đồ
        poll_interval=poll_interval,
        max_planning_time_ms=950.0,
        log_dir="logs/matches",
    )

    try:
        print("🚀 BẮT ĐẦU CHẠY BOT VÀ ĐỒNG BỘ TRẬN ĐẤU...")
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
        print(f"  👉 Xem lại diễn biến trận đấu tại: {web_url}")
        print("=" * 80 + "\n")

    except KeyboardInterrupt:
        print("\n[!] Người dùng đã dừng thực thi bot.")
    except (ProconAuthError, Exception) as e:
        if isinstance(e, ProconAuthError) or "401" in str(e) or "Unauthorized" in str(e):
            print("\n" + "=" * 80)
            print("❌ LỖI XÁC THỰC (HTTP 401 UNAUTHORIZED)")
            print("=" * 80)
            print(f"Server từ chối xác thực cho trận [{match_id}] với token hiện tại.")
            print(f"Chi tiết: {e}")
            print("\n👉 Gợi ý:")
            print("1. Kiểm tra lại Match ID xem đã tạo trên https://procon.ptit.edu.vn chưa.")
            print("2. Nếu trận yêu cầu token khác, bạn có thể truyền qua cờ -t:")
            print(f"   python run_match.py -m {match_id} -t <TOKEN_KHÁC>")
            print("=" * 80 + "\n")
        else:
            print(f"\n❌ LỖI TRONG QUÁ TRÌNH KẾT NỐI HOẶC THI ĐẤU: {e}")
            print("💡 Gợi ý xử lý:")
            print("   1. Kiểm tra kết nối mạng tới server https://procon.ptit.edu.vn")
            print("   2. Chạy thử nghiệm offline với cờ --mock để kiểm tra thuật toán:")
            print("      python run_match.py --mock")
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
        help="ID trận đấu tạo trên web (ví dụ: m-32744)",
    )
    parser.add_argument(
        "-t", "--token",
        type=str,
        default=None,
        help=f"Token xác thực (mặc định lấy từ .env hoặc {DEFAULT_BOT_TOKEN})",
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
        help="Chạy với Mock Server nội bộ (Offline Test)",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Tự động mở trình duyệt web khi trận bắt đầu (mặc định: Không mở, tự xem trên web)",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=float(os.getenv("PROCON_POLL_INTERVAL", 0.5)),
        help="Khoảng cách giữa các lần thăm dò server (giây, mặc định: 0.5)",
    )

    args = parser.parse_args()

    # Xác định match_id và chế độ chạy
    if args.mock:
        match_id = args.match or "mock_match_001"
        use_mock = True
    elif args.match:
        match_id = args.match.strip()
        use_mock = (match_id.lower() == "mock")
        if use_mock:
            match_id = "mock_match_001"
    else:
        # Người dùng không truyền -m: hỏi nhanh Match ID
        print_banner()
        print("💡 Nhập ID trận bạn đã tạo trên web (ví dụ: m-32744)")
        print("   hoặc gõ 'mock' để chạy thử nghiệm offline.")
        user_input = input("\n👉 Nhập Match ID: ").strip()
        if not user_input:
            user_input = "m-32744"
        if user_input.lower() == "mock":
            match_id = "mock_match_001"
            use_mock = True
        else:
            match_id = user_input
            use_mock = False

    token = resolve_token(match_id, args.token)

    play_match(
        match_id=match_id,
        token=token,
        base_url=args.url,
        use_mock=use_mock,
        open_browser=args.open_browser,
        poll_interval=args.poll,
    )


if __name__ == "__main__":
    main()
