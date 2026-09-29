const $ = (id) => document.getElementById(id);
const state = { metadata: null };

const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });
const number = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 });
const navNumber = new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 4 });

function queryBase() {
  return `fromDate=${encodeURIComponent($('fromDate').value)}&toDate=${encodeURIComponent($('toDate').value)}`;
}

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`;
    try { const body = await res.json(); message = body?.detail?.message || body?.detail || message; } catch (_) {}
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
  return res.json();
}

function showError(err) {
  const box = $('errorBox');
  box.textContent = err.message || String(err);
  box.classList.remove('hidden');
  setTimeout(() => box.classList.add('hidden'), 5000);
}

function emptyRow(cols, text='No purchase transactions found for these filters.') {
  return `<tr><td class="empty" colspan="${cols}">${text}</td></tr>`;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
}

async function loadOverview() {
  const d = await api(`/api/v1/dashboard/overview?${queryBase()}`);
  $('kpiAmount').textContent = money.format(d.totalInvestedAmount);
  $('kpiUnits').textContent = number.format(d.totalUnitsPurchased);
  $('kpiInvestors').textContent = number.format(d.investorCount);
  $('kpiFunds').textContent = number.format(d.mutualFundCount);
  $('kpiTransactions').textContent = number.format(d.transactionCount);
}

async function loadInvestorFunds() {
  const pan = $('investorSelect').value;
  const suffix = pan ? `&pan=${encodeURIComponent(pan)}` : '';
  const d = await api(`/api/v1/dashboard/investor-fund-summary?${queryBase()}${suffix}&pageSize=500`);
  const body = $('investorFundTable').querySelector('tbody');
  body.innerHTML = d.data.length ? d.data.map(r => `<tr>
    <td>${escapeHtml(r.pan)}</td><td>${escapeHtml(r.investorName)}</td><td>${escapeHtml(r.fundName)}</td>
    <td>${escapeHtml(r.amcCode)} / ${escapeHtml(r.fundCode)}</td><td class="num">${money.format(r.totalPurchaseAmount)}</td>
    <td class="num">${number.format(r.totalUnitsPurchased)}</td><td class="num">${r.transactionCount}</td>
  </tr>`).join('') : emptyRow(7);
}

async function loadFundInvestors() {
  const key = $('fundSelect').value;
  let suffix = '';
  if (key) {
    const [amcCode, fundCode] = key.split('|||');
    suffix = `&amcCode=${encodeURIComponent(amcCode)}&fundCode=${encodeURIComponent(fundCode)}`;
  }
  const d = await api(`/api/v1/dashboard/fund-investor-summary?${queryBase()}${suffix}&pageSize=500`);
  const body = $('fundInvestorTable').querySelector('tbody');
  body.innerHTML = d.data.length ? d.data.map(r => `<tr>
    <td>${escapeHtml(r.fund.fundName)}</td><td>${escapeHtml(r.fund.amcCode)} / ${escapeHtml(r.fund.fundCode)}</td>
    <td>${escapeHtml(r.investor.pan)}</td><td>${escapeHtml(r.investor.name)}</td><td class="num">${money.format(r.totalPurchaseAmount)}</td>
    <td class="num">${number.format(r.totalUnitsPurchased)}</td><td class="num">${r.transactionCount}</td>
  </tr>`).join('') : emptyRow(7);
}

async function loadInvestors() {
  const search = $('investorSearch').value.trim();
  const suffix = search ? `&search=${encodeURIComponent(search)}` : '';
  const d = await api(`/api/v1/dashboard/investors?${queryBase()}${suffix}&pageSize=500`);
  const body = $('investorTable').querySelector('tbody');
  body.innerHTML = d.data.length ? d.data.map(r => `<tr>
    <td>${escapeHtml(r.pan)}</td><td>${escapeHtml(r.investorName)}</td><td class="num">${money.format(r.totalInvestedAmount)}</td>
    <td class="num">${number.format(r.totalUnitsPurchased)}</td><td class="num">${r.mutualFundCount}</td><td class="num">${r.transactionCount}</td>
  </tr>`).join('') : emptyRow(6);
}

async function loadFunds() {
  const search = $('fundSearch').value.trim();
  const suffix = search ? `&search=${encodeURIComponent(search)}` : '';
  const d = await api(`/api/v1/dashboard/mutual-funds?${queryBase()}${suffix}&pageSize=500`);
  const body = $('fundTable').querySelector('tbody');
  body.innerHTML = d.data.length ? d.data.map(r => `<tr>
    <td>${escapeHtml(r.amcCode)}</td><td>${escapeHtml(r.fundCode)}</td><td>${escapeHtml(r.fundName)}</td>
    <td class="num">${money.format(r.totalInvestedAmount)}</td><td class="num">${number.format(r.totalUnitsPurchased)}</td>
    <td class="num">${navNumber.format(r.averageNav)}</td><td class="num">${r.investorCount}</td><td class="num">${r.transactionCount}</td>
  </tr>`).join('') : emptyRow(8);
}

async function refreshAll() {
  try { await Promise.all([loadOverview(), loadInvestorFunds(), loadFundInvestors(), loadInvestors(), loadFunds()]); }
  catch (e) { showError(e); }
}

function setupTabs() {
  document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    $(btn.dataset.tab).classList.add('active');
  }));
}

function exportTable(tableId) {
  const rows = [...$(tableId).querySelectorAll('tr')].map(row => [...row.cells].map(cell => {
    const value = cell.innerText.replace(/\s+/g, ' ').trim().replaceAll('"', '""');
    return `"${value}"`;
  }).join(','));
  const blob = new Blob([rows.join('\n')], {type:'text/csv;charset=utf-8;'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = `${tableId}-${$('fromDate').value}-to-${$('toDate').value}.csv`; a.click();
  URL.revokeObjectURL(url);
}

function debounce(fn, wait=250) {
  let timer; return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), wait); };
}

async function init() {
  setupTabs();
  try {
    state.metadata = await api('/api/v1/dashboard/metadata');
    $('fromDate').value = state.metadata.minDate;
    $('toDate').value = state.metadata.maxDate;
    $('fromDate').min = state.metadata.minDate; $('fromDate').max = state.metadata.maxDate;
    $('toDate').min = state.metadata.minDate; $('toDate').max = state.metadata.maxDate;

    state.metadata.investors.forEach(i => {
      const o = document.createElement('option'); o.value = i.pan; o.textContent = `${i.investorName} (${i.pan})`; $('investorSelect').appendChild(o);
    });
    state.metadata.funds.forEach(f => {
      const o = document.createElement('option'); o.value = `${f.amcCode}|||${f.fundCode}`; o.textContent = `${f.fundName} (${f.amcCode}/${f.fundCode})`; $('fundSelect').appendChild(o);
    });

    $('applyFilters').addEventListener('click', refreshAll);
    $('investorSelect').addEventListener('change', () => loadInvestorFunds().catch(showError));
    $('fundSelect').addEventListener('change', () => loadFundInvestors().catch(showError));
    $('investorSearch').addEventListener('input', debounce(() => loadInvestors().catch(showError)));
    $('fundSearch').addEventListener('input', debounce(() => loadFunds().catch(showError)));
    document.querySelectorAll('[data-export]').forEach(b => b.addEventListener('click', () => exportTable(b.dataset.export)));
    await refreshAll();
  } catch (e) { showError(e); }
}

init();
