:root {
  --primary: #0f4c81;
  --primary-dark: #0b3961;
  --gold: #f4c95d;
  --bg: #f4f7fb;
  --surface: #ffffff;
  --text: #1a2433;
  --muted: #5d6b82;
  --success: #1c9a67;
  --warning: #d8861c;
  --danger: #d94f4f;
  --border: #e5ebf4;
  --shadow: 0 12px 32px rgba(15, 76, 129, 0.12);
}

* {
  box-sizing: border-box;
}

html, body {
  margin: 0;
  font-family: 'Inter', sans-serif;
  background: var(--bg);
  color: var(--text);
}

a {
  color: inherit;
  text-decoration: none;
}

img {
  max-width: 100%;
}

.container {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
}

.site-header {
  background: rgba(255, 255, 255, 0.96);
  position: sticky;
  top: 0;
  z-index: 20;
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(8px);
}

.nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 76px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 800;
  font-size: 1.1rem;
}

.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
}

nav {
  display: flex;
  align-items: center;
  gap: 22px;
  font-weight: 500;
  color: var(--muted);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 12px;
  padding: 0.9rem 1.3rem;
  cursor: pointer;
  font-weight: 700;
  transition: 0.2s ease;
}

.btn:hover {
  transform: translateY(-1px);
}

.btn-primary {
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
}

.btn-secondary {
  background: var(--gold);
  color: var(--text);
}

.btn-light {
  background: #ecf2ff;
  color: var(--primary);
}

.small {
  padding: 0.65rem 1rem;
  font-size: 0.9rem;
}

.full {
  width: 100%;
}

.hero {
  background: linear-gradient(135deg, rgba(15, 76, 129, 0.06), rgba(244, 201, 93, 0.18));
  padding: 80px 0 70px;
}

.hero-inner {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 40px;
  align-items: center;
}

.eyebrow {
  display: inline-block;
  margin-bottom: 16px;
  background: rgba(15, 76, 129, 0.08);
  color: var(--primary);
  padding: 0.4rem 0.75rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.hero-copy h1 {
  font-size: clamp(2.4rem, 4vw, 4rem);
  line-height: 1.05;
  margin: 0 0 18px;
}

.hero-copy p {
  font-size: 1.08rem;
  line-height: 1.8;
  color: var(--muted);
  max-width: 620px;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-top: 28px;
}

.stats-row {
  display: flex;
  gap: 28px;
  margin-top: 30px;
  flex-wrap: wrap;
}

.stats-row div {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stats-row strong {
  font-size: 1.6rem;
}

.stats-row span {
  color: var(--muted);
}

.hero-card {
  display: grid;
  gap: 20px;
}

.mini-panel {
  background: var(--surface);
  border-radius: 24px;
  box-shadow: var(--shadow);
  padding: 24px;
}

.mini-panel h3 {
  margin: 18px 0 8px;
}

.tag {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 700;
  padding: 0.45rem 0.8rem;
}

.tag.success {
  background: rgba(28, 154, 103, 0.12);
  color: var(--success);
}

.tag.warning {
  background: rgba(216, 134, 28, 0.12);
  color: var(--warning);
}

.subtle {
  background: linear-gradient(135deg, rgba(15, 76, 129, 0.08), rgba(244, 201, 93, 0.16));
}

.features, .page-section {
  padding: 80px 0;
}

.section-heading {
  margin-bottom: 32px;
  text-align: center;
}

.section-heading.left {
  text-align: left;
}

.section-heading h2 {
  margin: 0;
  font-size: clamp(2rem, 3vw, 2.8rem);
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 22px;
}

.feature-card, .resource-card, .class-card, .panel, .auth-card, .contact-box {
  background: var(--surface);
  border-radius: 22px;
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
}

.feature-card {
  padding: 28px 22px;
}

.icon {
  width: 54px;
  height: 54px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  background: rgba(15, 76, 129, 0.08);
  font-size: 1.8rem;
}

.feature-card h3 {
  margin: 18px 0 12px;
}

.feature-card p {
  color: var(--muted);
  line-height: 1.7;
  margin: 0;
}

.cta-banner {
  padding: 0 0 90px;
}

.cta-inner {
  background: linear-gradient(135deg, var(--primary-dark), var(--primary));
  color: white;
  border-radius: 28px;
  padding: 34px 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.auth-section {
  padding: 80px 0;
}

.auth-wrap {
  display: flex;
  justify-content: center;
}

.auth-card {
  width: min(540px, 100%);
  padding: 32px;
}

.auth-card h2,
.auth-card h3 {
  margin-top: 0;
}

form {
  display: grid;
  gap: 18px;
}

label {
  display: grid;
  gap: 8px;
  font-weight: 600;
  color: var(--text);
}

input, textarea {
  width: 100%;
  border-radius: 12px;
  border: 1px solid var(--border);
  padding: 0.9rem 1rem;
  font-size: 1rem;
  font-family: 'Inter', sans-serif;
  background: #f9fbff;
}

textarea {
  resize: vertical;
}

.demo-box {
  margin-top: 24px;
  padding-top: 18px;
  border-top: 1px solid var(--border);
  color: var(--muted);
}

.demo-box ul {
  margin: 10px 0 0;
  padding-left: 18px;
  line-height: 1.8;
}

.dashboard {
  padding: 60px 0 90px;
}

.dashboard-shell {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 28px;
}

.sidebar {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 24px 18px;
  height: fit-content;
  box-shadow: var(--shadow);
}

.sidebar h3 {
  margin: 0 0 8px;
}

.sidebar p {
  margin: 0 0 18px;
  color: var(--muted);
}

.sidebar ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 12px;
}

.sidebar a {
  color: var(--muted);
  font-weight: 600;
}

.dashboard-main {
  display: grid;
  gap: 24px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
}

.stat-card {
  background: linear-gradient(135deg, rgba(15, 76, 129, 0.06), rgba(244, 201, 93, 0.18));
  border-radius: 18px;
  padding: 22px 18px;
  border: 1px solid var(--border);
}

.stat-card span {
  display: block;
  color: var(--muted);
  margin-bottom: 8px;
}

.stat-card strong {
  font-size: 2rem;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.panel {
  padding: 24px;
}

.panel h3 {
  margin-top: 0;
}

.list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 16px;
}

.list li {
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 10px;
}

.full-width {
  width: 100%;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th, .data-table td {
  border-bottom: 1px solid var(--border);
  padding: 14px 10px;
  text-align: left;
}

.resource-grid, .class-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24px;
}

.resource-card, .class-card {
  padding: 24px;
}

.resource-top {
  margin-bottom: 14px;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  color: var(--muted);
  margin: 18px 0;
  gap: 10px;
  font-size: 0.9rem;
  flex-wrap: wrap;
}

.class-card {
  display: grid;
  gap: 12px;
}

.class-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.narrow {
  max-width: 1100px;
}

.support-grid {
  display: grid;
  grid-template-columns: 0.9fr 1.1fr;
  gap: 26px;
  align-items: start;
}

.support-form {
  min-width: 0;
}

.contact-box {
  padding: 24px;
  margin-top: 30px;
}

.success-note {
  padding: 14px 16px;
  border-radius: 12px;
  background: rgba(28, 154, 103, 0.12);
  color: var(--success);
  margin-bottom: 18px;
  font-weight: 600;
}

.site-footer {
  background: #0e1d2f;
  color: rgba(255, 255, 255, 0.8);
  padding: 52px 0 30px;
}

.footer-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr;
  gap: 26px;
}

.site-footer h4 {
  color: white;
  margin-bottom: 14px;
}

.site-footer ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

@media (max-width: 980px) {
  .feature-grid,
  .resource-grid,
  .stats-grid,
  .panel-grid,
  .support-grid,
  .hero-inner,
  .footer-grid {
    grid-template-columns: 1fr 1fr;
  }

  .dashboard-shell {
    display: block;
  }

  .sidebar {
    margin-bottom: 22px;
  }
}

@media (max-width: 720px) {
  nav {
    gap: 12px;
    font-size: 0.85rem;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .feature-grid,
  .resource-grid,
  .stats-grid,
  .panel-grid,
  .support-grid,
  .hero-inner,
  .footer-grid {
    grid-template-columns: 1fr;
  }

  .cta-inner {
    display: grid;
    text-align: center;
  }

  .nav {
    align-items: flex-start;
    padding: 16px 0;
    flex-direction: column;
    gap: 14px;
  }
}

@media (prefers-reduced-motion: no-preference) {
  .btn, .feature-card, .resource-card {
    transition: transform 0.25s ease, box-shadow 0.25s ease;
  }

  .feature-card:hover, .resource-card:hover, .class-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 20px 40px rgba(15, 76, 129, 0.12);
  }
}


















































