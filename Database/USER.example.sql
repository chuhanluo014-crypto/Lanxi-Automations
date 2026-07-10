CREATE USER IF NOT EXISTS 'xhs_user'@'localhost' IDENTIFIED BY 'your_password';
CREATE USER IF NOT EXISTS 'xhs_user'@'127.0.0.1' IDENTIFIED BY 'your_password';

GRANT ALL PRIVILEGES ON xhs_ip_lab.* TO 'xhs_user'@'localhost';
GRANT ALL PRIVILEGES ON xhs_ip_lab.* TO 'xhs_user'@'127.0.0.1';

FLUSH PRIVILEGES;
