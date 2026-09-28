# Git Branch Strategy & Workflow Guidelines

## 1. Branch Model

Dự án áp dụng mô hình phân nhánh rút gọn dựa trên **Git Flow / GitHub Flow**:

```text
main (production-ready / stable releases)
  ▲
  │ (pull request & code review)
develop (integration branch)
  ▲
  ├── feature/m0-client-protocol
  ├── feature/m1-hexgrid-simulator
  ├── feature/m2-dp-planner
  ├── feature/m3-single-qlearning
  ├── feature/m4-marl-iql
  ├── feature/m5-hybrid-strategy
  ├── exp/run-baseline-vs-marl
  └── fix/server-timeout-handling
```

### Các nhánh chính

- **`main`**: Nhánh ổn định cao nhất, chứa mã nguồn đã kiểm thử và sẵn sàng thi đấu / nộp bài. Tuyệt đối không commit trực tiếp vào `main`.
- **`develop`**: Nhánh tích hợp các tính năng đã hoàn thiện trước khi release lên `main`.
- **`feature/<tên-tính-năng>`**: Nhánh phát triển tính năng mới. Tách từ `develop` và merge lại vào `develop` qua PR.
- **`exp/<tên-thí-nghiệm>`**: Nhánh thực hiện các sweep thí nghiệm, benchmark, vẽ biểu đồ mà không ảnh hưởng mã nguồn chính.
- **`fix/<tên-lỗi>`**: Nhánh sửa lỗi nóng hoặc lỗi logic.

---

## 2. Commit Message Conventions (Conventional Commits)

Định dạng commit chuẩn:
```text
<type>(<scope>): <mô tả ngắn bằng tiếng Anh hoặc tiếng Việt>
```

### Các `type` được chấp nhận:
- `feat`: Thêm tính năng mới (ví dụ: `feat(dp): implement value iteration for hex grid`)
- `fix`: Sửa lỗi (ví dụ: `fix(client): handle 401 token expired gracefully`)
- `docs`: Cập nhật tài liệu (ví dụ: `docs: update phase 0 checklist in README`)
- `test`: Thêm hoặc sửa unit tests (ví dụ: `test(marl): add test cases for iql step`)
- `refactor`: Tái cấu trúc code mà không đổi hành vi (ví dụ: `refactor(env): optimize neighbor lookup in hex grid`)
- `perf`: Cải thiện hiệu năng tính toán Bellman update
- `chore`: Thay đổi file build, cấu hình, gitignore, requirements

---

## 3. Quy tắc bảo mật và Token

> [!CAUTION]
> **TUYỆT ĐỐI KHÔNG COMMIT TOKEN HOẶC THÔNG TIN BẢO MẬT LÊN GIT REPOSITORY!**
> 
> - Luôn lưu token trong `.env` (đã được đưa vào `.gitignore`).
> - Trước khi `git commit` hoặc `git push`, hãy kiểm tra `git status` và `git diff` để đảm bảo không có file chứa credentials.
> - Nếu lỡ commit token, lập tức thu hồi token cũ trên web PROCON và tạo token mới.

---

## 4. Quy trình làm việc hàng ngày

1. Kéo mã nguồn mới nhất:
   ```bash
   git checkout develop
   git pull origin develop
   ```
2. Tạo nhánh mới:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Lập trình và kiểm thử:
   ```bash
   python -m unittest discover tests
   ```
4. Commit theo chuẩn và đẩy lên remote:
   ```bash
   git add .
   git commit -m "feat(module): your message"
   git push origin feature/your-feature-name
   ```
5. Tạo Pull Request vào `develop` để đồng đội review.
