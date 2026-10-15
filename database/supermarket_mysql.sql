-- =====================================================================
--  Супермаркет: проста база даних MySQL, що відповідає сайту (Django-застосунок inventory)
--  Таблиці названо так само, як у Django, поля збігаються з моделями сайту.
--  MySQL Workbench: File -> Open SQL Script... -> Execute (перша блискавка).
--  ERD: Database -> Reverse Engineer...
-- =====================================================================
CREATE DATABASE IF NOT EXISTS supermarket CHARACTER SET utf8mb4;
USE supermarket;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS inventory_orderitem;
DROP TABLE IF EXISTS inventory_order;
DROP TABLE IF EXISTS inventory_product;
DROP TABLE IF EXISTS inventory_category;
DROP TABLE IF EXISTS auth_user;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. Користувачі сайту (admin, worker) — спрощена auth_user
CREATE TABLE auth_user (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    username     VARCHAR(150) NOT NULL UNIQUE,
    is_superuser TINYINT(1)   NOT NULL DEFAULT 0
);

-- 2. Категорії товарів (модель Category)
CREATE TABLE inventory_category (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT         NOT NULL
);

-- 3. Товари (модель Product)
CREATE TABLE inventory_product (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(150)  NOT NULL,
    description    TEXT          NOT NULL,
    price          DECIMAL(10,2) NOT NULL,
    stock_quantity INT           NOT NULL DEFAULT 0,
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    category_id    INT           NOT NULL,
    FOREIGN KEY (category_id) REFERENCES inventory_category (id)
);

-- 4. Замовлення (модель Order)
CREATE TABLE inventory_order (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    created_by_id  INT           NULL,
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status         VARCHAR(20)   NOT NULL DEFAULT 'unpaid',   -- unpaid / paid
    total_amount   DECIMAL(12,2) NOT NULL DEFAULT 0,
    stock_deducted TINYINT(1)    NOT NULL DEFAULT 0,
    FOREIGN KEY (created_by_id) REFERENCES auth_user (id) ON DELETE SET NULL
);

-- 5. Позиції замовлення (модель OrderItem)
CREATE TABLE inventory_orderitem (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    order_id   INT           NOT NULL,
    product_id INT           NOT NULL,
    quantity   INT           NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    UNIQUE (order_id, product_id),
    FOREIGN KEY (order_id)   REFERENCES inventory_order (id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES inventory_product (id)
);

-- ---------------------------------------------------------------------
--  Дані з вашого сайту (db.sqlite3)
-- ---------------------------------------------------------------------
INSERT INTO auth_user (id, username, is_superuser) VALUES
    (1, 'admin', 1),
    (2, 'worker', 0);

INSERT INTO inventory_category (id, name, description) VALUES
    (1, 'Молочні продукти', ''),
    (2, 'Напої', ''),
    (3, 'Хліб і випічка', ''),
    (4, 'Бакалія', '');

INSERT INTO inventory_product (id, name, description, price, stock_quantity, created_at, category_id) VALUES
    (1, 'Молоко 2.5% 900 мл', '', 42.9, 118, '2026-10-12 07:05:57', 1),
    (2, 'Сир кисломолочний 5%', '', 38.5, 8, '2026-10-12 07:05:57', 1),
    (3, 'Йогурт натуральний', '', 24, 45, '2026-10-12 07:05:57', 1),
    (4, 'Масло вершкове 180 г', '', 89.9, 30, '2026-10-12 07:05:57', 1),
    (5, 'Вода мінеральна 1.5 л', '', 24, 194, '2026-10-12 07:05:57', 2),
    (6, 'Сік яблучний 1 л', '', 51, 58, '2026-10-12 07:05:57', 2),
    (7, 'Чай чорний 25 пак.', '', 62, 7, '2026-10-12 07:05:57', 2),
    (8, 'Хліб пшеничний', '', 22, 39, '2026-10-12 07:05:57', 3),
    (9, 'Круасан', '', 18, 3, '2026-10-12 07:05:57', 3),
    (10, 'Багет', '', 27.5, 25, '2026-10-12 07:05:57', 3),
    (11, 'Гречка 1 кг', '', 56, 78, '2026-10-12 07:05:57', 4),
    (12, 'Рис 1 кг', '', 49, 70, '2026-10-12 07:05:57', 4),
    (13, 'Олія соняшникова 1 л', '', 72, 55, '2026-10-12 07:05:57', 4);

INSERT INTO inventory_order (id, created_by_id, created_at, status, total_amount, stock_deducted) VALUES
    (1, 2, '2026-10-12 07:05:57', 'paid', 219.8, 1),
    (2, 2, '2026-10-12 07:05:57', 'unpaid', 240, 0),
    (3, 2, '2026-10-12 07:05:57', 'paid', 282, 1);

INSERT INTO inventory_orderitem (id, order_id, product_id, quantity, unit_price) VALUES
    (1, 1, 1, 2, 42.9),
    (2, 1, 8, 1, 22),
    (3, 1, 11, 2, 56),
    (4, 2, 11, 3, 56),
    (5, 2, 13, 1, 72),
    (6, 3, 5, 6, 24),
    (7, 3, 9, 2, 18),
    (8, 3, 6, 2, 51);

-- Перевірка кількості записів
SELECT 'auth_user' AS tbl, COUNT(*) AS rows_count FROM auth_user
UNION ALL SELECT 'inventory_category', COUNT(*) FROM inventory_category
UNION ALL SELECT 'inventory_product', COUNT(*) FROM inventory_product
UNION ALL SELECT 'inventory_order', COUNT(*) FROM inventory_order
UNION ALL SELECT 'inventory_orderitem', COUNT(*) FROM inventory_orderitem;
