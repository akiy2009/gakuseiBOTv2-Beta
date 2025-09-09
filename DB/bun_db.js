const { argv } = Bun;

const db = await Bun.sql({
  client: "mysql",
  connection: {
    host: "$localhost",
    user: "$user",
    password: "$yourpassword",
    database: "$database",
  },
});

async function migrate(feature) {
  if (feature === "remind") {
    await db.query(`
      CREATE TABLE IF NOT EXISTS reminders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT NOT NULL,
        message TEXT NOT NULL,
        remind_at DATETIME NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }
  if (feature === "study") {
    await db.query(`
      CREATE TABLE IF NOT EXISTS study_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT NOT NULL,
        subject VARCHAR(255),
        duration INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }
  if (feature === "ranking") {
    await db.query(`
      CREATE TABLE IF NOT EXISTS rankings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT NOT NULL,
        score INT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }
  console.log(JSON.stringify({ status: "ok", feature }));
}

async function addRemind(userId, message, remindAt) {
  await db.query(
    "INSERT INTO reminders (user_id, message, remind_at) VALUES (?, ?, ?)",
    [userId, message, remindAt]
  );
  console.log(JSON.stringify({ status: "ok", feature: "remind", action: "add" }));
}

async function listRemind(userId) {
  const rows = await db.query("SELECT * FROM reminders WHERE user_id = ?", [userId]);
  console.log(JSON.stringify(rows));
}

async function main() {
  const command = argv[2];
  const feature = argv[3];

  if (command === "migrate") {
    await migrate(feature);
  } else if (command === "add" && feature === "remind") {
    const [userId, message, remindAt] = argv.slice(4);
    await addRemind(userId, message, remindAt);
  } else if (command === "list" && feature === "remind") {
    const userId = argv[4];
    await listRemind(userId);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
