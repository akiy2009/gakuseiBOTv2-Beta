import Bun from "bun";

const db = Bun.sql({
  client: "mysql",
  connection: {
    host: "localhost",
    user: "root",
    password: "yourpassword",
    database: "gakusei"
  }
});

const input = await Bun.stdin.readAll();
const data = JSON.parse(new TextDecoder().decode(input));

await db.insert("{}").values(data).run();
