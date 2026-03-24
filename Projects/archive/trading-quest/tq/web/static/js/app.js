/* Trading Quest Dashboard JS */

document.addEventListener('DOMContentLoaded', function() {
    // Load strategies on index page
    var stratList = document.getElementById('strategy-list');
    if (stratList) {
        fetch('/api/strategies')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                stratList.innerHTML = '';
                (data.strategies || []).forEach(function(name) {
                    var li = document.createElement('li');
                    li.textContent = name;
                    stratList.appendChild(li);
                });
            })
            .catch(function() {
                stratList.innerHTML = '<li>Failed to load strategies</li>';
            });
    }

    // Load data status on index page
    var dataStatus = document.getElementById('data-status');
    if (dataStatus) {
        fetch('/api/data/status')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                dataStatus.innerHTML =
                    '<p>Daily rows: ' + (data.daily_rows || 0) + '</p>' +
                    '<p>Minute rows: ' + (data.minute_rows || 0) + '</p>' +
                    '<p>Universe: ' + (data.universe_count || 0) + ' symbols</p>';
            })
            .catch(function() {
                dataStatus.textContent = 'Cache not initialized';
            });
    }

    // Quest form
    var questForm = document.getElementById('quest-form');
    if (questForm) {
        questForm.addEventListener('submit', function(e) {
            e.preventDefault();
            var fd = new FormData(questForm);
            var symbols = fd.get('symbols').split(',').map(function(s) { return s.trim(); });
            var payload = {
                quest_id: fd.get('quest_id'),
                market: fd.get('market'),
                symbols: symbols,
                strategy: fd.get('strategy'),
                days: parseInt(fd.get('days')),
                capital: parseFloat(fd.get('capital')),
                start_date: '2024-01-15'
            };
            fetch('/api/quest/' + payload.quest_id + '/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var resultDiv = document.getElementById('quest-result');
                var resultJson = document.getElementById('result-json');
                if (resultDiv && resultJson) {
                    resultDiv.style.display = 'block';
                    resultJson.textContent = JSON.stringify(data, null, 2);
                }
            })
            .catch(function(err) {
                alert('Error: ' + err.message);
            });
        });
    }

    // Backdata Inventory (index page summary)
    var invContent = document.getElementById('inventory-content');
    if (invContent) {
        fetch('/api/data/inventory')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) {
                    invContent.innerHTML = '<p style="color:#ef4444">오류: ' + data.error + '</p>';
                    return;
                }

                function fmtNum(n) {
                    return n != null ? Number(n).toLocaleString('ko-KR') : '-';
                }
                function fmtPrice(n) {
                    if (n == null) return '-';
                    var v = Number(n);
                    if (v >= 1000) return v.toLocaleString('ko-KR', { maximumFractionDigits: 0 });
                    if (v >= 1) return v.toFixed(2);
                    return v.toFixed(4);
                }
                function fmtBytes(b) {
                    if (!b) return '-';
                    if (b >= 1048576) return (b / 1048576).toFixed(1) + ' MB';
                    if (b >= 1024) return (b / 1024).toFixed(1) + ' KB';
                    return b + ' B';
                }
                function period(min, max) {
                    return (min && max) ? (min + ' ~ ' + max) : '-';
                }

                var totalSymbols = data.markets.reduce(function (a, m) { return a + m.symbol_count; }, 0);
                var totalCandles = data.markets.reduce(function (a, m) { return a + m.total_candles; }, 0);

                var html = '<div style="display:flex;gap:2rem;flex-wrap:wrap;margin-bottom:1rem;">'
                    + '<div><div style="font-size:0.75rem;color:var(--text-secondary,#64748b);text-transform:uppercase">DB 크기</div><div style="font-size:1.1rem;font-weight:700">' + fmtBytes(data.db_size_bytes) + '</div></div>'
                    + '<div><div style="font-size:0.75rem;color:var(--text-secondary,#64748b);text-transform:uppercase">총 종목</div><div style="font-size:1.1rem;font-weight:700">' + fmtNum(totalSymbols) + '</div></div>'
                    + '<div><div style="font-size:0.75rem;color:var(--text-secondary,#64748b);text-transform:uppercase">총 캔들</div><div style="font-size:1.1rem;font-weight:700">' + fmtNum(totalCandles) + '</div></div>'
                    + '</div>';

                if (data.markets.length === 0) {
                    html += '<p style="color:var(--text-secondary,#64748b)">저장된 백데이터가 없습니다.</p>';
                } else {
                    // Summary table
                    html += '<table style="margin-bottom:1.25rem">'
                        + '<thead><tr><th>시장</th><th>종목수</th><th>총 캔들</th><th>기간</th></tr></thead><tbody>';
                    data.markets.forEach(function (m) {
                        html += '<tr>'
                            + '<td>' + m.market + '</td>'
                            + '<td>' + fmtNum(m.symbol_count) + '</td>'
                            + '<td>' + fmtNum(m.total_candles) + '</td>'
                            + '<td>' + period(m.min_date, m.max_date) + '</td>'
                            + '</tr>';
                    });
                    html += '</tbody></table>';

                    // Per-market collapsible detail
                    var byMarket = {};
                    data.symbols.forEach(function (s) {
                        if (!byMarket[s.market]) byMarket[s.market] = [];
                        byMarket[s.market].push(s);
                    });

                    Object.keys(byMarket).sort().forEach(function (market) {
                        var rows = byMarket[market];
                        var tid = 'inv-tbl-' + market.replace(/[^a-zA-Z0-9]/g, '_');
                        html += '<details style="margin-bottom:0.75rem;border:1px solid var(--border,#e2e8f0);border-radius:6px;overflow:hidden">'
                            + '<summary style="padding:0.6rem 1rem;cursor:pointer;font-weight:600;background:var(--card-bg,#fff)">'
                            + market + ' &nbsp;<span style="color:var(--text-secondary,#64748b);font-weight:400;font-size:0.85rem">'
                            + fmtNum(rows.length) + '종목</span>'
                            + '</summary>'
                            + '<table id="' + tid + '">'
                            + '<thead><tr><th>종목</th><th>일수</th><th>시작</th><th>종료</th><th>현재가 (수정주가)</th></tr></thead><tbody>';
                        rows.forEach(function (r) {
                            html += '<tr>'
                                + '<td style="font-weight:600;font-family:monospace">' + r.symbol + '</td>'
                                + '<td>' + fmtNum(r.candle_count) + '</td>'
                                + '<td>' + (r.min_date || '-') + '</td>'
                                + '<td>' + (r.max_date || '-') + '</td>'
                                + '<td>' + fmtPrice(r.latest_close) + '</td>'
                                + '</tr>';
                        });
                        html += '</tbody></table></details>';
                    });

                    html += '<p style="text-align:right;margin-top:0.5rem">'
                        + '<a href="/data" style="color:var(--primary,#2563eb);font-size:0.85rem">전체 백데이터 보기 &rarr;</a></p>';
                }

                invContent.innerHTML = html;
            })
            .catch(function (err) {
                invContent.innerHTML = '<p style="color:#ef4444">데이터를 불러오지 못했습니다: ' + err + '</p>';
            });
    }

    // Leaderboard
    var lbBody = document.getElementById('leaderboard-body');
    if (lbBody) {
        fetch('/api/leaderboard')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var board = data.leaderboard || [];
                if (board.length === 0) {
                    lbBody.innerHTML = '<tr><td colspan="7">No strategies evaluated yet.</td></tr>';
                    return;
                }
                lbBody.innerHTML = '';
                board.forEach(function(r, i) {
                    var tr = document.createElement('tr');
                    tr.innerHTML =
                        '<td>' + (i + 1) + '</td>' +
                        '<td>' + r.strategy_name + '</td>' +
                        '<td>' + (r.total_return_pct || 0).toFixed(2) + '%</td>' +
                        '<td>' + (r.win_rate || 0).toFixed(1) + '%</td>' +
                        '<td>' + ((r.max_drawdown || 0) * 100).toFixed(2) + '%</td>' +
                        '<td>' + (r.sharpe_ratio || 0).toFixed(2) + '</td>' +
                        '<td>' + (r.rank_score || 0).toFixed(1) + '</td>';
                    lbBody.appendChild(tr);
                });
            })
            .catch(function() {
                lbBody.innerHTML = '<tr><td colspan="7">Failed to load leaderboard</td></tr>';
            });
    }
});
