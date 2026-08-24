"use client";

import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";

type View = "overview" | "customers" | "imports";

type Customer = {
  id: string;
  name: string;
  email: string;
  initials: string;
  segment: string;
  orders: number;
  value: number;
  lastOrder: string;
  category: string;
  tone: string;
};

type ApiCustomer = {
  customer_id: string;
  segment: string;
  recency_days: number;
  frequency: number;
  monetary_value: string;
  favorite_category: string | null;
};

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");

const defaultSegments = [
  { name: "Champions", count: 68, value: 18420, color: "#1d5b4f" },
  { name: "Loyal customers", count: 59, value: 12680, color: "#d5744f" },
  { name: "Promising", count: 47, value: 7420, color: "#eabf72" },
  { name: "At risk", count: 39, value: 6160, color: "#8c728f" },
  { name: "New customers", count: 36, value: 2690, color: "#78a7a2" },
  { name: "Hibernating", count: 35, value: 1250, color: "#c9c3b7" },
];

const demoCustomers: Customer[] = [
  { id: "CW-1084", name: "Ava Morgan", email: "ava.morgan@example.com", initials: "AM", segment: "Champions", orders: 14, value: 2480, lastOrder: "2 days ago", category: "Outerwear", tone: "sage" },
  { id: "CW-0921", name: "Noah Williams", email: "noah.w@example.com", initials: "NW", segment: "Loyal customers", orders: 9, value: 1765, lastOrder: "6 days ago", category: "Footwear", tone: "clay" },
  { id: "CW-1176", name: "Mia Chen", email: "mia.chen@example.com", initials: "MC", segment: "Promising", orders: 4, value: 890, lastOrder: "8 days ago", category: "Knitwear", tone: "gold" },
  { id: "CW-0743", name: "Ethan James", email: "ethan.j@example.com", initials: "EJ", segment: "At risk", orders: 11, value: 1940, lastOrder: "74 days ago", category: "Denim", tone: "plum" },
  { id: "CW-1215", name: "Sofia Patel", email: "sofia.p@example.com", initials: "SP", segment: "New customers", orders: 1, value: 185, lastOrder: "1 day ago", category: "Accessories", tone: "blue" },
  { id: "CW-0688", name: "Leo Martinez", email: "leo.m@example.com", initials: "LM", segment: "Hibernating", orders: 2, value: 240, lastOrder: "162 days ago", category: "Tops", tone: "stone" },
  { id: "CW-1032", name: "Isla Thompson", email: "isla.t@example.com", initials: "IT", segment: "Champions", orders: 12, value: 2210, lastOrder: "3 days ago", category: "Dresses", tone: "sage" },
  { id: "CW-0997", name: "Lucas Brown", email: "lucas.b@example.com", initials: "LB", segment: "Loyal customers", orders: 8, value: 1495, lastOrder: "12 days ago", category: "Bottoms", tone: "clay" },
];

const segmentTones: Record<string, string> = {
  Champions: "sage",
  "Loyal customers": "clay",
  Promising: "gold",
  "At risk": "plum",
  "New customers": "blue",
  Hibernating: "stone",
};

function customerFromApi(customer: ApiCustomer): Customer {
  const identity = customer.customer_id;
  const localPart = identity.includes("@") ? identity.split("@")[0] : identity;
  const name = localPart
    .split(/[._-]+/)
    .filter(Boolean)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ") || identity;
  const initials = name.split(/\s+/).slice(0, 2).map(part => part.charAt(0)).join("").toUpperCase();
  return {
    id: identity,
    name,
    email: identity.includes("@") ? identity : `Customer ID · ${identity}`,
    initials,
    segment: customer.segment,
    orders: customer.frequency,
    value: Number(customer.monetary_value),
    lastOrder: customer.recency_days === 0 ? "Today" : `${customer.recency_days} days ago`,
    category: customer.favorite_category ?? "—",
    tone: segmentTones[customer.segment] ?? "stone",
  };
}

const revenuePoints = [36, 41, 38, 47, 45, 53, 51, 61, 58, 67, 64, 76];

function money(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const paths: Record<string, React.ReactNode> = {
    overview: <><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></>,
    customers: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></>,
    upload: <><path d="M12 3v12M7 8l5-5 5 5"/><path d="M5 21h14a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    refresh: <><path d="M20 7h-5V2"/><path d="M20 7a9 9 0 1 0 1 8"/></>,
    trend: <><path d="m3 17 6-6 4 4 8-9"/><path d="M15 6h6v6"/></>,
    arrow: <path d="m9 18 6-6-6-6"/>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    menu: <><path d="M4 7h16M4 12h16M4 17h16"/></>,
    close: <><path d="M6 6l12 12M18 6 6 18"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function Sidebar({ view, setView, open, close, customerCount }: { view: View; setView: (view: View) => void; open: boolean; close: () => void; customerCount: number }) {
  const navigate = (next: View) => { setView(next); close(); };
  return (
    <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
      <div className="brand-row">
        <div className="brand-mark"><span>C</span></div>
        <div><strong>CustomWear</strong><span>Analytics</span></div>
        <button className="icon-button sidebar-close" onClick={close} aria-label="Close navigation"><Icon name="close"/></button>
      </div>
      <nav aria-label="Dashboard navigation">
        <p className="nav-label">Workspace</p>
        <button className={view === "overview" ? "active" : ""} onClick={() => navigate("overview")}><Icon name="overview"/>Overview</button>
        <button className={view === "customers" ? "active" : ""} onClick={() => navigate("customers")}><Icon name="customers"/>Customers<span className="nav-count">{customerCount}</span></button>
        <button className={view === "imports" ? "active" : ""} onClick={() => navigate("imports")}><Icon name="upload"/>Data imports</button>
      </nav>
      <div className="sidebar-note">
        <span className="pulse-dot"/>Demo workspace
        <p>Connect your FastAPI URL to use live PostgreSQL data.</p>
      </div>
      <div className="profile-card">
        <span className="avatar avatar-dark">AC</span>
        <div><strong>Anthony Chan</strong><span>Administrator</span></div>
        <Icon name="arrow" size={16}/>
      </div>
    </aside>
  );
}

function Header({ title, onMenu, connection }: { title: string; onMenu: () => void; connection: string }) {
  return <header className="topbar">
    <button className="icon-button mobile-menu" onClick={onMenu} aria-label="Open navigation"><Icon name="menu"/></button>
    <div><p className="eyebrow">Customer intelligence</p><h1>{title}</h1></div>
    <div className="topbar-actions">
      <span className={`status-pill ${connection}`}><span className="pulse-dot"/>{connection === "live" ? "Live PostgreSQL" : connection === "offline" ? "API offline" : "Demo data"}</span>
      <button className="icon-button" aria-label="Notifications"><Icon name="bell"/><span className="notification-dot"/></button>
    </div>
  </header>;
}

function Overview({ onViewCustomers, runStatus, onRun, segmentData }: { onViewCustomers: () => void; runStatus: string; onRun: () => void; segmentData: typeof defaultSegments }) {
  const path = `M 0 ${220-revenuePoints[0]*2} ${revenuePoints.map((point,index)=>`L ${index*(720/11)} ${220-point*2}`).join(" ")}`;
  const customerCount = segmentData.reduce((total, segment) => total + segment.count, 0);
  return <>
    <section className="welcome-row">
      <div><h2>Good morning, Anthony.</h2><p>Here’s how your customer base is moving this month.</p></div>
      <button className="primary-button" onClick={onRun} disabled={runStatus === "running"}><Icon name="refresh"/>{runStatus === "running" ? "Analyzing…" : "Run segmentation"}</button>
    </section>

    {runStatus === "complete" && <div className="success-banner"><span><Icon name="check"/></span>Segmentation complete. {customerCount} customer profiles were refreshed.</div>}
    {runStatus === "failed" && <div className="error-banner">The analytics API could not complete this run. Check the backend connection and try again.</div>}

    <section className="metric-grid" aria-label="Key performance indicators">
      <article className="metric-card"><div><span>Total revenue</span><strong>$48,620</strong></div><span className="metric-icon green"><Icon name="trend"/></span><p><b>+12.4%</b> from last month</p></article>
      <article className="metric-card"><div><span>Active customers</span><strong>{customerCount}</strong></div><span className="metric-icon clay"><Icon name="customers"/></span><p><b>+8.1%</b> from last month</p></article>
      <article className="metric-card"><div><span>Average order</span><strong>$86.42</strong></div><span className="metric-icon gold"><Icon name="overview"/></span><p><b>+3.7%</b> from last month</p></article>
      <article className="metric-card"><div><span>Repeat purchase rate</span><strong>68.4%</strong></div><span className="metric-icon plum"><Icon name="refresh"/></span><p><b>+5.2%</b> from last month</p></article>
    </section>

    <section className="analytics-grid">
      <article className="panel revenue-panel">
        <div className="panel-heading"><div><p className="eyebrow">Performance</p><h3>Revenue momentum</h3></div><select aria-label="Revenue period" defaultValue="12"><option value="12">Last 12 weeks</option><option value="6">Last 6 weeks</option></select></div>
        <div className="chart-summary"><strong>$48,620</strong><span>+12.4%</span></div>
        <div className="line-chart" aria-label="Revenue increased over the last 12 weeks">
          <div className="y-labels"><span>$12k</span><span>$8k</span><span>$4k</span><span>$0</span></div>
          <svg viewBox="0 0 720 220" preserveAspectRatio="none" role="img" aria-label="Weekly revenue trend">
            <defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#1d5b4f" stopOpacity=".28"/><stop offset="100%" stopColor="#1d5b4f" stopOpacity="0"/></linearGradient></defs>
            {[28,84,140,196].map(y => <line key={y} x1="0" x2="720" y1={y} y2={y} className="grid-line"/>)}
            <path className="area" d={`${path} L 720 220 L 0 220 Z`}/>
            <path className="trend-line" d={path}/>
            {revenuePoints.map((point,index)=><circle key={index} cx={index*(720/11)} cy={220-point*2} r="3.5"/>)}
          </svg>
          <div className="x-labels"><span>Jun 2</span><span>Jun 23</span><span>Jul 14</span><span>Aug 4</span><span>Aug 18</span></div>
        </div>
      </article>

      <article className="panel segment-panel">
        <div className="panel-heading"><div><p className="eyebrow">RFM model</p><h3>Customer segments</h3></div><button className="text-button" onClick={onViewCustomers}>View all <Icon name="arrow" size={15}/></button></div>
        <div className="donut-wrap">
          <div className="donut" role="img" aria-label="Customer distribution across six segments"><div><strong>{customerCount}</strong><span>customers</span></div></div>
          <div className="segment-legend">{segmentData.map(segment => <div key={segment.name}><span className="legend-dot" style={{background:segment.color}}/><p>{segment.name}<small>{money(segment.value)} value</small></p><strong>{segment.count}</strong></div>)}</div>
        </div>
      </article>
    </section>

    <section className="lower-grid">
      <article className="panel opportunity-panel">
        <div className="panel-heading"><div><p className="eyebrow">Recommended action</p><h3>Retention opportunity</h3></div><span className="spark-badge">39 customers</span></div>
        <div className="opportunity-content"><div className="opportunity-number">$6.1k<span>at-risk value</span></div><p>Your at-risk customers previously purchased <b>2.4× more</b> outerwear than average. A focused fall-arrivals campaign could reactivate this group.</p><button className="secondary-button" onClick={onViewCustomers}>Review at-risk customers <Icon name="arrow" size={16}/></button></div>
      </article>
      <article className="panel category-panel">
        <div className="panel-heading"><div><p className="eyebrow">Product affinity</p><h3>Top categories</h3></div></div>
        <div className="category-bars">{[["Outerwear",86,"$12.4k"],["Knitwear",69,"$9.8k"],["Footwear",57,"$8.2k"],["Denim",43,"$6.1k"]].map(([label,width,value])=><div key={label as string}><span>{label}</span><div><i style={{width:`${width}%`}}/></div><strong>{value}</strong></div>)}</div>
      </article>
    </section>
  </>;
}

function CustomersView({ onSelect, data }: { onSelect: (customer: Customer) => void; data: Customer[] }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("All segments");
  const visible = useMemo(() => data.filter(customer => {
    const matchesQuery = `${customer.name} ${customer.email} ${customer.id}`.toLowerCase().includes(query.toLowerCase());
    return matchesQuery && (filter === "All segments" || customer.segment === filter);
  }), [data, query, filter]);
  return <section className="page-section">
    <div className="section-intro"><div><h2>Customer profiles</h2><p>Explore behavioral segments generated from transaction history.</p></div><button className="secondary-button"><Icon name="upload"/>Export CSV</button></div>
    <div className="panel table-panel">
      <div className="table-toolbar"><label className="search-box"><Icon name="search"/><input value={query} onChange={event=>setQuery(event.target.value)} placeholder="Search name, email, or ID" aria-label="Search customers"/></label><select value={filter} onChange={event=>setFilter(event.target.value)} aria-label="Filter by segment"><option>All segments</option>{defaultSegments.map(segment=><option key={segment.name}>{segment.name}</option>)}</select><span>{visible.length} profiles</span></div>
      <div className="table-scroll"><table><thead><tr><th>Customer</th><th>Segment</th><th>Orders</th><th>Lifetime value</th><th>Last order</th><th>Top category</th><th><span className="sr-only">Open</span></th></tr></thead><tbody>{visible.map(customer=><tr key={customer.id} onClick={()=>onSelect(customer)} tabIndex={0} onKeyDown={event=>event.key==="Enter"&&onSelect(customer)}><td><span className={`avatar ${customer.tone}`}>{customer.initials}</span><div><strong>{customer.name}</strong><small>{customer.email}</small></div></td><td><span className={`segment-chip ${customer.segment.toLowerCase().replaceAll(" ","-")}`}>{customer.segment}</span></td><td>{customer.orders}</td><td><strong>{money(customer.value)}</strong></td><td>{customer.lastOrder}</td><td>{customer.category}</td><td><Icon name="arrow" size={16}/></td></tr>)}</tbody></table></div>
      {visible.length === 0 && <div className="empty-state"><span><Icon name="search"/></span><h3>No customers found</h3><p>Try a different name or segment filter.</p></div>}
    </div>
  </section>;
}

function ImportsView() {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState("idle");
  const chooseFile = (event: ChangeEvent<HTMLInputElement>) => { setFile(event.target.files?.[0] ?? null); setUploadStatus("idle"); };
  const importFile = async () => {
    if (!file) return;
    setUploadStatus("running");
    if (!API_BASE) {
      window.setTimeout(() => setUploadStatus("complete"), 700);
      return;
    }
    try {
      const rows = (await file.text()).trim().split(/\r?\n/);
      const headers = rows.shift()?.split(",").map(value => value.trim()) ?? [];
      const expected = ["external_id","customer_id","order_id","sku","category","quantity","unit_price","purchased_at"];
      if (headers.join(",") !== expected.join(",")) throw new Error("Invalid CSV headers");
      const transactions = rows.filter(Boolean).map(row => {
        const values = row.split(",").map(value => value.trim());
        const record = Object.fromEntries(headers.map((header,index) => [header,values[index]]));
        return { ...record, quantity: Number(record.quantity), unit_price: Number(record.unit_price) };
      });
      const response = await fetch(`${API_BASE}/api/v1/transactions/batch`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ transactions }) });
      if (!response.ok) throw new Error("Import failed");
      setUploadStatus("complete");
    } catch {
      setUploadStatus("failed");
    }
  };
  return <section className="page-section imports-page">
    <div className="section-intro"><div><h2>Transaction imports</h2><p>Add purchase history to refresh customer segments and insights.</p></div></div>
    <div className="import-grid">
      <article className="panel upload-panel"><div className="upload-icon"><Icon name="upload" size={25}/></div><h3>Upload transaction data</h3><p>Choose a CSV containing transaction ID, customer ID, order ID, SKU, category, quantity, price, and purchase date.</p><input ref={input} hidden type="file" accept=".csv" onChange={chooseFile}/><button className="primary-button" onClick={()=>input.current?.click()}>Choose CSV file</button><span className="file-limit">CSV only · up to 5,000 rows</span>{file && <div className="selected-file"><span><Icon name="check"/></span><div><strong>{file.name}</strong><small>Ready to import</small></div><button onClick={()=>{setFile(null);setUploadStatus("idle")}} aria-label="Remove selected file"><Icon name="close" size={16}/></button></div>}{file && uploadStatus !== "complete" && <button className="secondary-button full-button" onClick={importFile} disabled={uploadStatus === "running"}>{uploadStatus === "running" ? "Importing…" : "Import transactions"}</button>}{uploadStatus === "complete" && <div className="success-banner compact"><span><Icon name="check"/></span>Import completed successfully.</div>}{uploadStatus === "failed" && <div className="error-banner compact">Import failed. Verify the CSV headers and API connection.</div>}</article>
      <article className="panel import-history"><div className="panel-heading"><div><p className="eyebrow">Activity</p><h3>Recent imports</h3></div></div>{[["summer-orders.csv","1,240 rows","Aug 22, 2026"],["july-transactions.csv","982 rows","Aug 1, 2026"],["spring-archive.csv","2,108 rows","Jul 14, 2026"]].map(([name,rows,date])=><div className="history-row" key={name}><span><Icon name="check"/></span><div><strong>{name}</strong><small>{rows} · {date}</small></div><em>Complete</em></div>)}</article>
    </div>
    <article className="panel schema-panel"><div><p className="eyebrow">CSV template</p><h3>Expected columns</h3><p>Use these exact headers so the API can validate and ingest every record.</p></div><div className="column-list">{["external_id","customer_id","order_id","sku","category","quantity","unit_price","purchased_at"].map(column=><code key={column}>{column}</code>)}</div></article>
  </section>;
}

function CustomerDrawer({ customer, close }: { customer: Customer | null; close: () => void }) {
  if (!customer) return null;
  return <div className="drawer-backdrop" onClick={close}><aside className="drawer" onClick={event=>event.stopPropagation()} aria-label={`${customer.name} profile`}><button className="icon-button drawer-close" onClick={close} aria-label="Close customer profile"><Icon name="close"/></button><div className="drawer-profile"><span className={`avatar avatar-large ${customer.tone}`}>{customer.initials}</span><h2>{customer.name}</h2><p>{customer.email}</p><span className={`segment-chip ${customer.segment.toLowerCase().replaceAll(" ","-")}`}>{customer.segment}</span></div><div className="drawer-stats"><div><span>Lifetime value</span><strong>{money(customer.value)}</strong></div><div><span>Total orders</span><strong>{customer.orders}</strong></div><div><span>Last purchase</span><strong>{customer.lastOrder}</strong></div><div><span>Favorite category</span><strong>{customer.category}</strong></div></div><div className="rfm-card"><p className="eyebrow">RFM profile</p><h3>Behavior scores</h3>{[["Recency",customer.segment==="At risk"?2:5],["Frequency",Math.min(5,Math.ceil(customer.orders/3))],["Monetary",customer.value>1500?5:customer.value>700?4:2]].map(([label,score])=><div className="score-row" key={label as string}><span>{label}</span><div>{[1,2,3,4,5].map(index=><i key={index} className={index<=(score as number)?"filled":""}/>)}</div><strong>{score}/5</strong></div>)}</div><button className="primary-button full-button">Create campaign audience</button></aside></div>;
}

export default function Home() {
  const [view, setView] = useState<View>("overview");
  const [navOpen, setNavOpen] = useState(false);
  const [selected, setSelected] = useState<Customer | null>(null);
  const [runStatus, setRunStatus] = useState("idle");
  const [connection, setConnection] = useState(API_BASE ? "checking" : "demo");
  const [segmentData, setSegmentData] = useState(defaultSegments);
  const [customerData, setCustomerData] = useState(demoCustomers);
  useEffect(() => {
    if (!API_BASE) return;
    Promise.all([
      fetch(`${API_BASE}/health/live`),
      fetch(`${API_BASE}/api/v1/segments/summary`),
      fetch(`${API_BASE}/api/v1/customers?limit=200`),
    ]).then(async ([health,summary,customerResponse]) => {
      if (!health.ok) throw new Error("API offline");
      setConnection("live");
      if (summary.ok) {
        const payload = await summary.json();
        const colors = defaultSegments.map(segment => segment.color);
        setSegmentData(payload.segments.map((segment: { segment: string; customer_count: number; total_value: string }, index: number) => ({ name: segment.segment, count: segment.customer_count, value: Number(segment.total_value), color: colors[index % colors.length] })));
      }
      if (customerResponse.ok) {
        const payload = await customerResponse.json();
        setCustomerData(payload.items.map(customerFromApi));
      }
    }).catch(() => setConnection("offline"));
  }, []);
  const runSegmentation = async () => {
    setRunStatus("running");
    if (!API_BASE) { window.setTimeout(()=>setRunStatus("complete"), 1200); return; }
    try {
      const response = await fetch(`${API_BASE}/api/v1/segments/run`, { method: "POST" });
      if (!response.ok) throw new Error("Segmentation failed");
      setRunStatus("complete");
    } catch { setRunStatus("failed"); }
  };
  const titles: Record<View,string> = { overview:"Overview", customers:"Customers", imports:"Data imports" };
  return <div className="app-shell">
    <Sidebar view={view} setView={setView} open={navOpen} close={()=>setNavOpen(false)} customerCount={segmentData.reduce((total, segment) => total + segment.count, 0)}/>
    {navOpen && <button className="nav-backdrop" onClick={()=>setNavOpen(false)} aria-label="Close navigation"/>}
    <main className="main-content"><Header title={titles[view]} onMenu={()=>setNavOpen(true)} connection={connection}/><div className="content-wrap">
      {view === "overview" && <Overview onViewCustomers={()=>setView("customers")} runStatus={runStatus} onRun={runSegmentation} segmentData={segmentData}/>} 
      {view === "customers" && <CustomersView onSelect={setSelected} data={customerData}/>} 
      {view === "imports" && <ImportsView/>}
    </div><footer>CustomWear Analytics <span>·</span> Customer intelligence powered by PostgreSQL</footer></main>
    <CustomerDrawer customer={selected} close={()=>setSelected(null)}/>
  </div>;
}
