// copyDist.cjs: copy built files to project root 'dist' directory for Vercel static build
const fs = require('fs');
const path = require('path');

// Source directory (dashboard-js/dist)
const srcDir = path.resolve(__dirname, 'dist');
// Destination directory (project root/dist)
const destDir = path.resolve(__dirname, '..', 'dist');

if (!fs.existsSync(srcDir)) {
  console.error('Source dist directory does not exist:', srcDir);
  process.exit(1);
}

fs.mkdirSync(destDir, { recursive: true });
fs.cpSync(srcDir, destDir, { recursive: true });
console.log('Copied', srcDir, 'to', destDir);
