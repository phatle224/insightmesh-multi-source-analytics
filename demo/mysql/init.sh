#!/bin/sh
set -eu

# No shell tracing: credentials must not enter the container logs.
mysql --protocol=socket -uroot -p"$MYSQL_ROOT_PASSWORD" <<SQL
CREATE DATABASE IF NOT EXISTS insightmesh_demo CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS 'demo_reader'@'%' IDENTIFIED BY '${DEMO_READER_PASSWORD}';
ALTER USER 'demo_reader'@'%' IDENTIFIED BY '${DEMO_READER_PASSWORD}';
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'demo_reader'@'%';
GRANT SELECT ON insightmesh_demo.* TO 'demo_reader'@'%';

USE insightmesh_demo;
CREATE TABLE IF NOT EXISTS foundation_probe (
  id INT PRIMARY KEY,
  label VARCHAR(100) NOT NULL
);
CREATE TABLE IF NOT EXISTS customers (
  id INT PRIMARY KEY,
  customer_name VARCHAR(255) NOT NULL,
  region VARCHAR(50) NOT NULL,
  created_at DATE NOT NULL
);
CREATE TABLE IF NOT EXISTS categories (
  id INT PRIMARY KEY,
  category_name VARCHAR(100) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS products (
  id INT PRIMARY KEY,
  category_id INT NOT NULL,
  product_name VARCHAR(255) NOT NULL,
  unit_price DECIMAL(12,2) NOT NULL,
  CONSTRAINT fk_products_category FOREIGN KEY (category_id) REFERENCES categories(id)
);
CREATE TABLE IF NOT EXISTS orders (
  id INT PRIMARY KEY,
  customer_id INT NOT NULL,
  ordered_at DATETIME NOT NULL,
  status ENUM('completed', 'cancelled', 'pending', 'refunded') NOT NULL,
  CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers(id)
);
CREATE TABLE IF NOT EXISTS order_items (
  order_id INT NOT NULL,
  product_id INT NOT NULL,
  quantity INT NOT NULL,
  unit_price DECIMAL(12,2) NOT NULL,
  PRIMARY KEY (order_id, product_id),
  CONSTRAINT fk_items_order FOREIGN KEY (order_id) REFERENCES orders(id),
  CONSTRAINT fk_items_product FOREIGN KEY (product_id) REFERENCES products(id)
);

INSERT IGNORE INTO foundation_probe VALUES (1, 'foundation-ready');
INSERT IGNORE INTO customers VALUES
  (1, 'Acme Retail', 'North', '2024-01-10'),
  (2, 'Bluebird Market', 'South', '2024-02-14'),
  (3, 'Cedar Goods', 'Central', '2024-03-22'),
  (4, 'Delta Outfitters', 'West', '2024-05-05'),
  (5, 'Evergreen Shop', 'East', '2024-06-18');
INSERT IGNORE INTO categories VALUES (1, 'Electronics'), (2, 'Home'), (3, 'Outdoors');
INSERT IGNORE INTO products VALUES
  (1, 1, 'Wireless Keyboard', 79.00), (2, 1, 'USB-C Hub', 49.00),
  (3, 2, 'Desk Lamp', 65.00), (4, 2, 'Storage Basket', 28.00),
  (5, 3, 'Daypack', 95.00), (6, 3, 'Insulated Bottle', 32.00);
INSERT IGNORE INTO orders VALUES
  (1001, 1, '2025-01-05 09:30:00', 'completed'),
  (1002, 2, '2025-01-08 14:10:00', 'completed'),
  (1003, 1, '2025-02-03 11:20:00', 'completed'),
  (1004, 3, '2025-02-12 16:45:00', 'cancelled'),
  (1005, 4, '2025-03-01 08:15:00', 'completed'),
  (1006, 5, '2025-03-16 13:05:00', 'refunded'),
  (1007, 2, '2025-04-02 10:00:00', 'pending'),
  (1008, 3, '2025-04-18 15:25:00', 'completed');
INSERT IGNORE INTO order_items VALUES
  (1001, 1, 2, 79.00), (1001, 3, 1, 65.00),
  (1002, 2, 3, 49.00), (1002, 4, 2, 28.00),
  (1003, 5, 1, 95.00), (1003, 6, 2, 32.00),
  (1004, 3, 2, 65.00), (1005, 5, 2, 95.00),
  (1005, 1, 1, 79.00), (1006, 4, 4, 28.00),
  (1007, 2, 1, 49.00), (1008, 6, 3, 32.00),
  (1008, 3, 1, 65.00);
FLUSH PRIVILEGES;
SQL
