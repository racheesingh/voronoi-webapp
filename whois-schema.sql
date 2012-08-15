drop table if exists subnets;
create table subnets (
  id integer primary key autoincrement,
  subnet string not null,
  lon integer,
  lat integer
);
