module.exports = {
  apps: [
    {
      name: "tiktok-affiliate-bot",
      script: "bot.py",
      interpreter: "python3",
      restart_delay: 3000,
      env: {
        NODE_ENV: "production",
      }
    },
    {
      name: "tiktok-affiliate-dashboard",
      script: "dashboard.py",
      interpreter: "python3",
      restart_delay: 3000,
      env: {
        NODE_ENV: "production",
        FLASK_APP: "dashboard.py"
      }
    }
  ]
};
