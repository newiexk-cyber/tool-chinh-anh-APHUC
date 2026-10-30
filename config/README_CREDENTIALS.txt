HƯỚNG DẪN CẤU HÌNH GOOGLE API CREDENTIALS
=========================================

1. Đặt file xác thực Google API vào thư mục này với tên:
   credentials.json
   (Đường dẫn đầy đủ: photo-retouch-automation/config/credentials.json)

2. Loại tài khoản Google API hỗ trợ:
   - Service Account Key (.json): Thêm email của Service Account (dạng xxx@yyy.iam.gserviceaccount.com)
     vào quyền "Chỉnh sửa" (Editor) của file Google Sheet và thư mục Google Drive của tiệm ảnh.
   - Hoặc OAuth 2.0 Client ID Desktop app.

3. Chế độ Mock Data tự động:
   - Nếu chưa có file credentials.json, hệ thống sẽ tự động bật "Chế độ Mô phỏng (Mock Data)"
     với 5 khách hàng mẫu để bạn trải nghiệm toàn bộ quy trình trên Web Dashboard ngay lập tức.
