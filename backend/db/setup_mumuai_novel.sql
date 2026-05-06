-- 创建用户角色
CREATE ROLE mumuai_novel WITH
    LOGIN
    SUPERUSER
    CREATEDB
    CREATEROLE
    PASSWORD 'N8aEb8mtb8dhA6t5';

-- 创建数据库
CREATE DATABASE mumuai_novel
    WITH
    OWNER = mumuai_novel
    ENCODING = 'UTF8'
    LC_COLLATE = 'zh_CN.UTF-8'
    LC_CTYPE = 'zh_CN.UTF-8'
    TEMPLATE = template0;

-- 授予所有权限
GRANT ALL PRIVILEGES ON DATABASE mumuai_novel TO mumuai_novel;
