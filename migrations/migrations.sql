# 0.5.0
alter table channels change column descr topic text not null;
alter table channels change column `auto` auto_join tinyint(1) not null default '1';
alter table channels change column perm priv int(11) not null default '1';
alter table channels change column name name varchar(64) not null;
alter table channels drop primary key;
alter table channels drop column id;
alter table channels add primary key(name);
