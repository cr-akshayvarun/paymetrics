function autoHideFlashes() {
  const flashes = document.querySelectorAll('.flash-message');
  flashes.forEach(flash => {
    setTimeout(() => {
      flash.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
      flash.style.transform = 'translateX(120%) scale(0.9)';
      flash.style.opacity = '0';
      setTimeout(() => flash.remove(), 400);
    }, 4500);
  });
}

document.addEventListener('DOMContentLoaded', function () {
  autoHideFlashes();

  const currentPage = window.location.pathname;
  document.querySelectorAll('.nav-item').forEach(item => {
    const href = item.getAttribute('href');
    if (href && currentPage.startsWith(href)) {
      item.classList.add('active');
    }
  });

  document.querySelectorAll('.stat-card').forEach(card => {
    card.addEventListener('mousemove', e => {
      const rect = card.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      card.style.setProperty('--mouse-x', x + '%');
      card.style.setProperty('--mouse-y', y + '%');
    });
  });

  document.querySelectorAll('.category-bar').forEach(bar => {
    const target = bar.style.width || '0%';
    bar.style.width = '0%';
    setTimeout(() => { bar.style.width = target; }, 300);
  });
});

function updateTransactionCategory(txnId, category) {
  fetch(`/transactions/${txnId}/update-category`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        const badge = document.querySelector(`.txn-category[data-txn-id="${txnId}"]`);
        if (badge) {
          badge.textContent = category;
          badge.style.transform = 'scale(1.1)';
          setTimeout(() => { badge.style.transform = ''; }, 200);
        }
      }
    });
}

function deleteTransaction(txnId) {
  if (confirm('Delete this transaction?')) {
    const row = document.querySelector(`button[onclick="deleteTransaction(${txnId})"]`)?.closest('tr');
    if (row) {
      row.style.transition = 'all 0.3s ease';
      row.style.opacity = '0';
      row.style.transform = 'translateX(-20px)';
    }
    setTimeout(() => {
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = `/transactions/${txnId}/delete`;
      document.body.appendChild(form);
      form.submit();
    }, row ? 300 : 0);
  }
}
