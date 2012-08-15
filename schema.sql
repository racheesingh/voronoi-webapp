drop table if exists servers;
create table servers (
  id integer primary key autoincrement,
  serverName string not null,
  serverAdd string,
  lon integer,
  lat integer,
  priority integer,
  weight integer,
  port integer
);
