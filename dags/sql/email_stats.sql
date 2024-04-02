create table if not exists test.letter(
    id serial8 primary key ,
    from_ text,
    to_ text,
    date timestamp,
    subject text,
    message text,
    date_of_load timestamp
)