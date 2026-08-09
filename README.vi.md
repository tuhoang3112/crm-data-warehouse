[English](README.md)

# Xây dựng lại hệ thống dữ liệu CRM khi chuyển từ Pipedrive sang Rework CRM

## Bối cảnh

Công ty chuyển CRM từ **Pipedrive sang Rework CRM**. Tuy nhiên, hai hệ thống có cấu trúc dữ liệu và API hoàn toàn khác nhau.

**Vấn đề:** Data Warehouse cũ được xây dựng theo cấu trúc của Pipedrive nên không còn hoạt động sau khi chuyển đổi. Trong khi đó, team Sales vẫn cần theo dõi pipeline liên tục: deal đang ở stage nào, win rate ra sao, đâu là những lý do phổ biến khiến deal thất bại,...

**Mục tiêu:** Xây dựng lại ingestion pipeline và data model theo cấu trúc của Rework CRM, đồng thời giữ lại dữ liệu lịch sử đã được migrate từ Pipedrive để các báo cáo Sales không bị gián đoạn.

---

## Architecture

```text id="qvfjej"
Rework CRM API
      │
      ▼
Airbyte (self-hosted)  →  raw ingest, incremental sync
      │
      ▼
BigQuery (raw layer)
      │
      ▼
Dataform (staging)  →  clean data, extract custom fields
      │
      ▼
Dataform (mart)  →  Snowflake Schema: fact + dimension
      │
      ▼
Power BI
```

| Layer | Tool | Chi tiết |
|---|---|---|
| Data Ingestion | Airbyte | [`View Connector`](./airbyte-custom-connector/) |
| Data Warehouse | BigQuery | [`View Raw Layer`](./assets/bigquery-raw-layer.png) |
| Transformation & Modeling | Dataform | [`View Models`](./dataform/) |
| Analytics | Power BI | [`View Dashboard`](./sales_dashboard/) |

### Cấu trúc dữ liệu CRM

Dữ liệu CRM xoay quanh **Deal** và các thông tin liên quan như Contact, Account, Pipeline, Stage, User và Activity.

```
Lead / Contact
      │
      ▼
    Deal
      │
      ├── thuộc Pipeline
      │        └── Stage
      │
      ├── được phụ trách bởi User
      │
      ├── liên kết với Account
      │
      └── có các Activity
             ├── Call
             ├── Note
             └── Change Log
```

### Data Mart

Data Mart được thiết kế theo mô hình **Snowflake Schema**, bao gồm:

* `fact_deal` — mỗi dòng tương ứng với một deal
* `fact_deal_activity` — mỗi dòng tương ứng với một activity của deal như call, note, change log,...
* `dim_pipeline`, `dim_stage`, `dim_contact`, `dim_user` — các dimension table chứa thông tin mô tả phục vụ phân tích
* `dim_account` — lưu thông tin account/company, được tách riêng để dùng chung cho deal và contact

![Data Warehouse Architecture](assets/erd-datamart.png)

---

## Cách triển khai

### 1. Tìm hiểu và test API

Tìm hiểu các nhóm endpoint chính của Rework CRM như **Pipeline, Deal, Account và Contact** dựa trên API documentation.

Sau đó, test từng endpoint bằng **Postman** để kiểm tra response thực tế, cấu trúc dữ liệu, pagination và mối quan hệ giữa các endpoint trước khi xây dựng ingestion pipeline.

### 2. Pull data với Airbyte

Sử dụng **Airbyte self-hosted** và Low-code Connector Builder để đưa dữ liệu từ Rework CRM API vào BigQuery.

Một số điểm cần xử lý:

* API truyền credentials qua **request body** thay vì header.
* Pagination theo `page/limit` phải được config thủ công.
* Activity không có endpoint hỗ trợ bulk fetching, vì vậy sử dụng **parent-child stream**: pull danh sách deal trước, sau đó pull activity của từng deal.
* Thiết lập **Incremental Sync** để mỗi lần chạy chỉ lấy dữ liệu mới hoặc đã thay đổi, thay vì reload toàn bộ khoảng **25.000 deals và 25.000 contacts**.

### 3. Làm sạch dữ liệu với Dataform

Sau khi raw data được ingest vào BigQuery, sử dụng **Dataform** để xây dựng staging layer và chuẩn hóa dữ liệu trước khi đưa vào Data Mart.

Các bước xử lý chính:

* Parse các nested JSON field như `address`, `form`, `owners`.
* Xử lý **custom fields** được Rework lưu dưới dạng dynamic JSON array: `UNNEST` dữ liệu, sau đó pivot trở lại thành các column bằng `MAX(IF(...))`.
* Decode các giá trị được encode dưới dạng HTML hoặc Base64 với prefix đặc biệt.
* Loại bỏ duplicate bằng `QUALIFY ROW_NUMBER()`, giữ nguyên một record gốc thay vì aggregate và vô tình kết hợp giá trị từ nhiều record khác nhau.

### 4. Đối soát dữ liệu cũ từ Pipedrive

Đây là phần phức tạp nhất của quá trình migration.

Do dữ liệu cũ được import từ Pipedrive sang Rework, một số field trên Rework không phản ánh đúng dữ liệu thực tế nếu sử dụng trực tiếp.

Ví dụ, `created_at` trên Rework ghi nhận **thời điểm record được import**, không phải thời điểm deal hoặc contact thực sự được tạo. Ngày tạo gốc vì vậy phải được lấy từ custom field lưu lại giá trị từ Pipedrive.

Một số custom field cũng không có tên dễ đọc mà chỉ được lưu dưới dạng các chuỗi ký tự ngẫu nhiên. Các field này phải được đối chiếu trực tiếp với Rework UI để xác định field tương ứng.

Sau khi mapping, sử dụng `COALESCE` để ưu tiên giá trị gốc từ Pipedrive nếu tồn tại và fallback về giá trị của Rework nếu không có.

Nhờ đó, dữ liệu phản ánh **thời điểm sự kiện thực sự xảy ra**, thay vì thời điểm record được migrate sang CRM mới.

### 5. Xây dựng Data Mart

Từ staging layer đã được làm sạch và chuẩn hóa, xây dựng Data Mart theo mô hình **Snowflake Schema** với các fact và dimension table phục vụ phân tích.

Thông tin `account` xuất hiện ở cả deal và contact được tách thành `dim_account` riêng để giảm dữ liệu trùng lặp và giữ data model gọn hơn.

Data Mart sau đó được sử dụng làm data source cho **Power BI** để phân tích Sales Pipeline.

---

## Skills & Tools

* **API & Postman:** đọc API documentation, test endpoint, xử lý pagination và parent-child streams
* **Airbyte:** Low-code Connector Builder, Incremental Sync
* **BigQuery & SQL:** `JSON_VALUE`, `UNNEST`, `QUALIFY ROW_NUMBER()`, nested JSON, pivot custom fields
* **Dataform:** tổ chức transformation theo các layer `declarations → staging → mart`
* **Data Modeling:** Snowflake Schema, Fact & Dimension tables, ERD
* **Power BI:** kết nối Data Mart và xây dựng Sales Pipeline reporting

---

## Kết quả

Kết nối thành công **Rework CRM** với Data Warehouse và khôi phục data flow cho các báo cáo Power BI sau khi chuyển đổi CRM.

Pipeline mới đồng thời giữ lại và xử lý đúng dữ liệu lịch sử từ Pipedrive, giúp các chỉ số Sales Pipeline như **deal stage, win rate và lost reason** tiếp tục được theo dõi nhất quán.

Nhờ đó, team Sales có thể tiếp tục sử dụng các báo cáo hiện có mà không bị gián đoạn bởi quá trình CRM migration.

> **Note:** Dự án này được xây dựng dựa trên dữ liệu thực tế của doanh nghiệp. Các thông tin nhạy cảm đã được làm mờ hoặc ẩn, đồng thời các key, thông tin xác thực và dữ liệu bảo mật đã được loại bỏ nhằm đảm bảo tính bảo mật của doanh nghiệp.
