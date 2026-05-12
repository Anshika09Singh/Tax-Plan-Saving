const OLD_STANDARD_DEDUCTION = 50000;
const NEW_STANDARD_DEDUCTION = 75000;

const defaults = {
  salary: 900000,
  freelance: 0,
  business: 0,
  other: 25000,
  section80c: 80000,
  nps: 20000,
  medical: 15000,
  homeLoan: 0,
  educationLoan: 0,
  donations: 0,
};

const fields = [...document.querySelectorAll("[data-field]")];
let latestValues = { ...defaults };
let latestPlan = null;
let latestRecommendations = [];
const formatter = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 0,
});

function money(value) {
  return `Rs. ${formatter.format(Math.round(value))}`;
}

function formatMarkdown(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-bold">$1</strong>')
    .replace(/\n/g, '<br/>')
    .replace(/- (.*?)(<br\/>|$)/g, '<li class="ml-4 list-disc text-slate-300">$1</li>');
}

function readInputs() {
  return Object.fromEntries(
    fields.map((field) => {
      const val = field.value.replace(/,/g, "");
      return [field.dataset.field, Math.max(Number(val) || 0, 0)];
    })
  );
}

function slabTax(income, slabs) {
  return slabs.reduce((tax, [lower, upper, rate]) => {
    if (income <= lower) return tax;
    return tax + (Math.min(income, upper) - lower) * rate;
  }, 0);
}

function oldRegimeTax(taxableIncome) {
  const baseTax =
    taxableIncome <= 500000
      ? 0
      : slabTax(taxableIncome, [
          [250000, 500000, 0.05],
          [500000, 1000000, 0.2],
          [1000000, Number.POSITIVE_INFINITY, 0.3],
        ]);
  return {
    regime: "Old Regime",
    taxableIncome,
    baseTax,
    cess: baseTax * 0.04,
    totalTax: baseTax * 1.04,
  };
}

function newRegimeTax(taxableIncome) {
  const baseTax =
    taxableIncome <= 1200000
      ? 0
      : slabTax(taxableIncome, [
          [400000, 800000, 0.05],
          [800000, 1200000, 0.1],
          [1200000, 1600000, 0.15],
          [1600000, 2000000, 0.2],
          [2000000, 2400000, 0.25],
          [2400000, Number.POSITIVE_INFINITY, 0.3],
        ]);
  return {
    regime: "New Regime",
    taxableIncome,
    baseTax,
    cess: baseTax * 0.04,
    totalTax: baseTax * 1.04,
  };
}

function calculatePlan(values) {
  const grossIncome = values.salary + values.freelance + values.business + values.other;
  const deductionBreakup = {
    "80C": Math.min(values.section80c, 150000),
    "NPS 80CCD(1B)": Math.min(values.nps, 50000),
    "Health Insurance 80D": Math.min(values.medical, 25000),
    "Home Loan Interest": Math.min(values.homeLoan, 200000),
    "Education Loan Interest": values.educationLoan,
    "Eligible Donations": Math.min(values.donations, 100000),
  };
  const eligibleDeductions =
    Object.values(deductionBreakup).reduce((total, amount) => total + amount, 0) +
    OLD_STANDARD_DEDUCTION;

  const oldResult = oldRegimeTax(Math.max(grossIncome - eligibleDeductions, 0));
  const newResult = newRegimeTax(Math.max(grossIncome - NEW_STANDARD_DEDUCTION, 0));
  const best = oldResult.totalTax <= newResult.totalTax ? oldResult : newResult;
  const other = best === oldResult ? newResult : oldResult;

  return {
    grossIncome,
    eligibleDeductions,
    deductionBreakup,
    oldResult,
    newResult,
    bestRegime: best.regime,
    bestTax: best.totalTax,
    taxSavings: Math.max(other.totalTax - best.totalTax, 0),
  };
}

function normalizeServerPlan(summary) {
  return {
    grossIncome: summary.gross_income,
    eligibleDeductions: summary.eligible_deductions,
    deductionBreakup: summary.deduction_breakup,
    oldResult: {
      regime: summary.old_regime.regime,
      taxableIncome: summary.old_regime.taxable_income,
      baseTax: summary.old_regime.base_tax,
      cess: summary.old_regime.cess,
      totalTax: summary.old_regime.total_tax,
    },
    newResult: {
      regime: summary.new_regime.regime,
      taxableIncome: summary.new_regime.taxable_income,
      baseTax: summary.new_regime.base_tax,
      cess: summary.new_regime.cess,
      totalTax: summary.new_regime.total_tax,
    },
    bestRegime: summary.best_regime,
    bestTax: summary.best_tax,
    taxSavings: summary.tax_savings,
  };
}

function recommendations(values, plan) {
  const items = [];
  const remaining80c = Math.max(150000 - plan.deductionBreakup["80C"], 0);
  const remainingNps = Math.max(50000 - plan.deductionBreakup["NPS 80CCD(1B)"], 0);

  if (remaining80c) {
    items.push(`Invest up to ${money(remaining80c)} more in ELSS, PPF, EPF, term insurance, or tuition-fee eligible 80C options.`);
  }
  if (remainingNps) {
    items.push(`Use the additional NPS window of ${money(remainingNps)} under 80CCD(1B).`);
  }
  if (plan.deductionBreakup["Health Insurance 80D"] < 25000) {
    items.push("Consider health insurance premium planning to improve 80D utilization.");
  }
  if (values.freelance + values.business > 0) {
    items.push("Track professional expenses, invoices, software, travel, and office costs to reduce business taxable profit.");
  }
  items.push(
    plan.bestRegime === "Old Regime"
      ? "The old regime currently wins because deductions are doing meaningful work."
      : "The new regime currently wins because lower slab rates outweigh available deductions."
  );
  return items;
}

function reportText(plan, recs) {
  return [
    "Tax Saving Assistant - Financial Summary",
    "",
    `Gross income: ${money(plan.grossIncome)}`,
    `Eligible deductions including standard deduction: ${money(plan.eligibleDeductions)}`,
    `Old regime taxable income: ${money(plan.oldResult.taxableIncome)}`,
    `Old regime estimated tax: ${money(plan.oldResult.totalTax)}`,
    `New regime taxable income: ${money(plan.newResult.taxableIncome)}`,
    `New regime estimated tax: ${money(plan.newResult.totalTax)}`,
    `Recommended regime: ${plan.bestRegime}`,
    `Estimated tax saving from selected regime: ${money(plan.taxSavings)}`,
    "",
    "Deduction breakup:",
    ...Object.entries(plan.deductionBreakup).map(([label, amount]) => `- ${label}: ${money(amount)}`),
    "",
    "Recommendations:",
    ...recs.map((item) => `- ${item}`),
    "",
    "Note: This is an educational planning estimate and not a filing certificate.",
  ].join("\n");
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function updateBars(plan) {
  const maxTax = Math.max(plan.oldResult.totalTax, plan.newResult.totalTax, 1);
  document.getElementById("oldBar").style.width = `${Math.max((plan.oldResult.totalTax / maxTax) * 100, 4)}%`;
  document.getElementById("newBar").style.width = `${Math.max((plan.newResult.totalTax / maxTax) * 100, 4)}%`;
}

function renderDeductions(plan) {
  const limits = {
    "80C": 150000,
    "NPS 80CCD(1B)": 50000,
    "Health Insurance 80D": 25000,
    "Home Loan Interest": 200000,
    "Education Loan Interest": Math.max(plan.deductionBreakup["Education Loan Interest"], 1),
    "Eligible Donations": 100000,
  };

  document.getElementById("deductionList").innerHTML = Object.entries(plan.deductionBreakup)
    .map(([label, amount]) => {
      const percent = Math.min((amount / limits[label]) * 100, 100);
      return `
        <div class="deduction-row">
          <header><span>${label}</span><span>${money(amount)}</span></header>
          <div class="h-1.5 w-full bg-slate-800/50 rounded-full overflow-hidden">
            <div class="h-full bg-brand-500 transition-all duration-700" style="width:${Math.max(percent, 3)}%"></div>
          </div>
        </div>
      `;
    })
    .join("");
}

function render() {
  latestValues = readInputs();
  const plan = latestPlan || calculatePlan(latestValues);
  const recs = latestRecommendations.length ? latestRecommendations : recommendations(latestValues, plan);

  setText("grossIncome", money(plan.grossIncome));
  setText("eligibleDeductions", money(plan.eligibleDeductions));
  setText("bestTax", money(plan.bestTax));
  setText("taxSavings", money(plan.taxSavings));
  setText("heroIncome", money(plan.grossIncome));
  setText("heroDeduction", money(plan.eligibleDeductions));
  setText("heroSavings", money(plan.taxSavings));
  setText("heroTax", money(plan.bestTax));
  setText("heroRegime", plan.bestRegime);
  setText("bestBadge", plan.bestRegime);
  setText("oldTax", money(plan.oldResult.totalTax));
  setText("newTax", money(plan.newResult.totalTax));
  setText("oldTaxable", `Taxable income ${money(plan.oldResult.taxableIncome)}`);
  setText("newTaxable", `Taxable income ${money(plan.newResult.taxableIncome)}`);

  updateBars(plan);
  renderDeductions(plan);

  document.getElementById("recommendations").innerHTML = recs
    .map((item) => `<div class="recommendation-item">${item}</div>`)
    .join("");
  document.getElementById("report").value = reportText(plan, recs);
}

async function refreshFromServer() {
  latestValues = readInputs();
  latestPlan = calculatePlan(latestValues);
  latestRecommendations = recommendations(latestValues, latestPlan);
  render();

  try {
    const response = await fetch("/api/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(latestValues),
    });
    if (!response.ok) return;
    const data = await response.json();
    latestPlan = normalizeServerPlan(data.summary);
    latestRecommendations = data.recommendations;
    document.getElementById("report").value = data.report;
    render();
  } catch {
    render();
  }
}

async function loadStatus() {
    try {
        const response = await fetch("/api/status");
        const data = await response.json();
        document.getElementById("modelName").textContent = data.model;
        document.getElementById("aiStatusText").textContent = data.groqConfigured ? "Groq live" : "Groq key missing";
        document.getElementById("aiStatusDot").className = `h-2.5 w-2.5 rounded-full ${data.groqConfigured ? "bg-brand-500" : "bg-accent-coral"} animate-pulse`;
    } catch {
        document.getElementById("aiStatusText").textContent = "Static mode";
        document.getElementById("modelName").textContent = "Backend offline";
    }

    // Fetch User Info
    try {
        const userRes = await fetch("/api/user");
        if (userRes.ok) {
            const userData = await userRes.json();
            document.getElementById("userDisplayName").textContent = userData.full_name || userData.username;
        }
    } catch (err) {
        console.error("Failed to fetch user data");
    }
}

document.getElementById("logoutBtn").addEventListener("click", async () => {
    if (confirm("Are you sure you want to logout?")) {
        await fetch("/api/logout", { method: "POST" });
        window.location.href = "/login";
    }
});

fields.forEach((field) => {
  field.addEventListener("input", (e) => {
    // Strip non-numeric characters
    let rawValue = e.target.value.replace(/[^0-9]/g, "");
    if (rawValue === "") {
      e.target.value = "";
    } else {
      e.target.value = formatter.format(rawValue);
    }
    refreshFromServer();
  });
});

document.getElementById("resetBtn").addEventListener("click", () => {
  fields.forEach((field) => {
    field.value = defaults[field.dataset.field];
  });
  latestPlan = null;
  latestRecommendations = [];
  refreshFromServer();
});

document.getElementById("downloadBtn").addEventListener("click", () => {
  const blob = new Blob([document.getElementById("report").value], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "tax-saving-summary.txt";
  link.click();
  URL.revokeObjectURL(url);
});

document.getElementById("printBtn").addEventListener("click", () => {
  const content = document.getElementById("report").value;
  const printWindow = window.open('', '_blank');
  printWindow.document.write(`
    <html>
      <head>
        <title>Tax Strategy Report</title>
        <style>
          body { font-family: sans-serif; padding: 40px; color: #1e293b; line-height: 1.6; }
          h1 { color: #16a34a; border-bottom: 2px solid #16a34a; padding-bottom: 10px; }
          pre { white-space: pre-wrap; background: #f8fafc; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; }
          .footer { margin-top: 40px; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 20px; }
        </style>
      </head>
      <body>
        <h1>TaxFlow Strategy Report</h1>
        <pre>${content}</pre>
        <div class="footer">TaxFlow Engine • AI Optimized • Generated on ${new Date().toLocaleDateString()}</div>
      </body>
    </html>
  `);
  printWindow.document.close();
  printWindow.print();
});

document.getElementById("aiInsightsBtn").addEventListener("click", async () => {
  const button = document.getElementById("aiInsightsBtn");
  const panel = document.getElementById("aiInsights");
  button.disabled = true;
  button.textContent = "Thinking...";
  panel.textContent = "Groq is reviewing the tax plan...";
  try {
    const response = await fetch("/api/ai-insights", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(readInputs()),
    });
    const data = await response.json();
    panel.textContent = data.insights || data.error || "No AI insight was generated.";
  } catch {
    panel.textContent = "The AI backend is not reachable. Start the Flask server to use Groq.";
  } finally {
    button.disabled = false;
    button.textContent = "Generate AI";
  }
});

document.getElementById("askBtn").addEventListener("click", async () => {
  const question = document.getElementById("questionInput").value.trim();
  const answer = document.getElementById("chatAnswer");
  const button = document.getElementById("askBtn");
  if (!question) {
    answer.textContent = "Type a question about your tax plan first.";
    return;
  }
  button.disabled = true;
  button.textContent = "Asking...";
  answer.textContent = "Groq is preparing an answer from your current numbers...";
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...readInputs(), question }),
    });
    const data = await response.json();
    answer.innerHTML = formatMarkdown(data.answer || data.error || "No answer was generated.");
  } catch {
    answer.textContent = "The AI backend is not reachable. Start the Flask server to use Groq.";
  } finally {
    button.disabled = false;
    button.textContent = "Ask AI";
  }
});

loadStatus();
// Populate fields with defaults if empty
fields.forEach((field) => {
  if (!field.value && defaults[field.dataset.field] !== undefined) {
    field.value = formatter.format(defaults[field.dataset.field]);
  }
});
refreshFromServer();
