"""
dashboard_renderer.py
Dựng chuỗi HTML/CSS/JS (Chart.js) cho TỪNG TRANG của dashboard, nhúng qua
st.components.v1.html.

Thiết kế: mỗi lần gọi render_dashboard_html(..., active_page=...) chỉ trả về
HTML của ĐÚNG 1 trang (Tổng quan / Danh mục & Quốc gia / Kết quả ML). Việc
điều hướng giữa 3 trang giờ do Streamlit st.tabs() đảm nhiệm (ở app.py), nên
HTML ở đây không còn thanh nav/JS switch nội bộ nữa — mỗi trang là 1 iframe
độc lập, gọn và tách bạch rõ ràng, tránh gây hiểu nhầm filter áp dụng chéo
sang các trang không liên quan.

Toàn bộ config Chart.js / dữ liệu (D object, mkBar, từng biểu đồ) giữ NGUYÊN
như bản gốc — các đoạn tạo Chart đều tự kiểm tra `document.getElementById(...)`
trước khi vẽ, nên an toàn khi trang chỉ chứa 1 tập canvas.
"""

BOOTSTRAP_ICONS_CDN = (
    '<link rel="stylesheet" '
    'href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">'
)


def _page_overview(total_records, unique_videos, unique_channels, avg_engagement):
    return f"""
<div class="pg">
  <div class="mrow">
    <div class="mc"><div class="ml"><i class="bi bi-collection"></i> Tổng bản ghi</div>
      <div class="mv">{total_records:,}</div><div class="ms">dòng dữ liệu</div></div>
    <div class="mc"><div class="ml"><i class="bi bi-play-btn"></i> Video duy nhất</div>
      <div class="mv">{unique_videos:,}</div><div class="ms">unique video IDs</div></div>
    <div class="mc"><div class="ml"><i class="bi bi-broadcast"></i> Số kênh</div>
      <div class="mv">{unique_channels:,}</div><div class="ms">kênh YouTube</div></div>
    <div class="mc"><div class="ml"><i class="bi bi-graph-up-arrow"></i> Avg Engagement</div>
      <div class="mv">{avg_engagement:.2f}%</div><div class="ms">tỷ lệ tương tác TB</div></div>
  </div>

  <div class="g31">
    <div class="card"><div class="ct"><i class="bi bi-bar-chart"></i> Số video trending theo tháng</div>
      <canvas id="cMonthly"></canvas></div>
    <div class="card"><div class="ct"><i class="bi bi-clock-history"></i> Engagement theo giờ đăng</div>
      <canvas id="cHourly"></canvas></div>
  </div>

  <div class="g2">
    <div class="card"><div class="ct"><i class="bi bi-calendar-week"></i> Engagement theo thứ trong tuần — "ngày vàng"</div>
      <canvas id="cDow"></canvas></div>
    <div class="card"><div class="ct"><i class="bi bi-trophy"></i> Top 8 kênh có Engagement cao nhất</div>
      <div id="topCh"></div></div>
  </div>

  <div class="card">
    <div class="ct"><i class="bi bi-bar-chart-steps"></i> Phân bố Engagement Rate</div>
    <canvas id="cEngDist" style="max-height:220px"></canvas>
  </div>
</div>
"""


def _page_category_country():
    return """
<div class="pg">
  <div class="g2">
    <div class="card"><div class="ct"><i class="bi bi-grid"></i> Engagement Rate theo danh mục</div>
      <canvas id="cCat" style="max-height:340px"></canvas></div>
    <div class="card"><div class="ct"><i class="bi bi-table"></i> Bảng chi tiết danh mục</div>
      <div style="overflow-y:auto;max-height:340px">
        <table class="tbl" id="tCat"></table></div></div>
  </div>
  <div class="g2">
    <div class="card"><div class="ct"><i class="bi bi-globe"></i> Engagement Rate theo quốc gia</div>
      <canvas id="cCou"></canvas></div>
    <div class="card"><div class="ct"><i class="bi bi-pie-chart"></i> Phân bố video theo quốc gia</div>
      <canvas id="cCouPie"></canvas></div>
  </div>
</div>
"""


def _page_ml(best_model):
    return f"""
<div class="pg">
  <div class="mrow">
    <div class="mc"><div class="ml"><i class="bi bi-cpu"></i> Best Model</div>
      <div class="mv" style="font-size:1.1rem">{best_model['model']}</div>
      <div class="ms">hiệu suất cao nhất</div></div>
    <div class="mc"><div class="ml">R2 Score</div>
      <div class="mv">{best_model['r2']:.4f}</div><div class="ms">orig space</div></div>
    <div class="mc"><div class="ml">RMSE</div>
      <div class="mv">{best_model['rmse']:.4f}</div><div class="ms">orig space</div></div>
    <div class="mc"><div class="ml">R2 Log Space</div>
      <div class="mv">{best_model['r2_log']:.4f}</div><div class="ms">log-transformed</div></div>
  </div>
  <div class="g2">
    <div class="card"><div class="ct"><i class="bi bi-bar-chart"></i> R2 Score các mô hình (cao hơn = tốt hơn)</div>
      <canvas id="cR2"></canvas></div>
    <div class="card"><div class="ct"><i class="bi bi-bar-chart"></i> RMSE các mô hình (thấp hơn = tốt hơn)</div>
      <canvas id="cRMSE"></canvas></div>
  </div>
  <div class="g2">
    <div class="card"><div class="ct"><i class="bi bi-scatter-chart"></i> Actual vs Predicted Engagement Rate</div>
      <canvas id="cScatter"></canvas></div>
    <div class="card"><div class="ct"><i class="bi bi-bar-chart-line"></i> Phân phối Residuals</div>
      <canvas id="cRes"></canvas></div>
  </div>
  <div class="card" style="margin-top:14px">
    <div class="ct"><i class="bi bi-table"></i> Bảng so sánh tất cả mô hình</div>
    <table class="tbl" id="tMod"></table>
  </div>
</div>
"""


def render_dashboard_html(
    total_records, unique_videos, unique_channels, avg_engagement, best_model,
    monthly_j, category_j, country_j, hourly_j, top_ch_j, dow_j,
    model_j, pred_j, res_j, active_page="ov",
):
    """Trả về chuỗi HTML hoàn chỉnh cho ĐÚNG 1 trang (active_page: 'ov' | 'cat' | 'ml'),
    để nhúng vào st.components.v1.html bên trong sub-tab Streamlit tương ứng.

    Tham số *_j là các chuỗi JSON (đã serialize bằng utils.to_j) chứa dữ liệu
    cho từng biểu đồ. total_records/unique_videos/.../best_model là các số
    liệu Key Metrics đã tính sẵn ở app.py (theo filter hiện tại, chỉ áp dụng
    khi active_page='ov').
    """
    if active_page == "cat":
        page_html = _page_category_country()
    elif active_page == "ml":
        page_html = _page_ml(best_model)
    else:
        page_html = _page_overview(total_records, unique_videos, unique_channels, avg_engagement)

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
{BOOTSTRAP_ICONS_CDN}
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
:root{{
  --bg:#f7f8fb;--card:#ffffff;--card2:#f2f4f8;
  --p1:#7c3aed;--p2:#0891b2;--p3:#d97706;--p4:#059669;--p5:#e11d48;
  --tx:#1e293b;--ts:#64748b;--br:rgba(15,23,42,.10);
  --sh:0 1px 3px rgba(15,23,42,.06);
}}
body{{background:var(--bg);color:var(--tx);font-family:'Segoe UI',system-ui,sans-serif;min-height:auto;overflow-x:hidden;}}

/* PAGE WRAPPER */
.pg{{padding:2px 2px 14px;}}

/* METRIC ROW */
.mrow{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:14px;}}
.mc{{background:var(--card);border:1px solid var(--br);border-radius:13px;
  padding:18px;position:relative;overflow:hidden;transition:transform .2s;box-shadow:var(--sh);}}
.mc:hover{{transform:translateY(-2px);}}
.mc::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;}}
.mc:nth-child(1)::before{{background:linear-gradient(90deg,var(--p1),var(--p2));}}
.mc:nth-child(2)::before{{background:linear-gradient(90deg,var(--p2),var(--p4));}}
.mc:nth-child(3)::before{{background:linear-gradient(90deg,var(--p3),var(--p5));}}
.mc:nth-child(4)::before{{background:linear-gradient(90deg,var(--p4),var(--p2));}}
.ml{{font-size:.72rem;color:var(--ts);text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;
  display:flex;align-items:center;gap:6px;}}
.mv{{font-size:1.9rem;font-weight:800;
  background:linear-gradient(135deg,#0f172a,#475569);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;}}
.ms{{font-size:.72rem;color:var(--ts);margin-top:3px;}}

/* GRIDS */
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;}}
.g31{{display:grid;grid-template-columns:2fr 1fr;gap:14px;margin-bottom:14px;}}
.g13{{display:grid;grid-template-columns:1fr 2fr;gap:14px;margin-bottom:14px;}}

/* CARD */
.card{{background:var(--card);border:1px solid var(--br);border-radius:13px;padding:18px;
  box-shadow:var(--sh);margin-bottom:14px;}}
.ct{{font-size:.78rem;font-weight:600;color:var(--ts);text-transform:uppercase;
  letter-spacing:.07em;margin-bottom:14px;display:flex;align-items:center;gap:7px;}}
.ct i{{color:var(--p1);font-size:.85rem;}}
canvas{{max-height:250px;}}

/* TABLE */
.tbl{{width:100%;border-collapse:collapse;font-size:.8rem;}}
.tbl th{{text-align:left;padding:7px 10px;color:var(--ts);font-weight:500;
  border-bottom:1px solid var(--br);font-size:.72rem;text-transform:uppercase;}}
.tbl td{{padding:9px 10px;border-bottom:1px solid rgba(15,23,42,.05);color:var(--tx);}}
.tbl tr:hover td{{background:rgba(15,23,42,.03);}}
.bge{{display:inline-block;padding:2px 7px;border-radius:20px;font-size:.7rem;font-weight:600;}}
.bg-g{{background:rgba(5,150,105,.12);color:#059669;}}
.bg-r{{background:rgba(225,29,72,.12);color:#e11d48;}}
.bg-b{{background:rgba(8,145,178,.12);color:#0891b2;}}

/* BAR INLINE */
.bw{{display:flex;align-items:center;gap:8px;}}
.bb{{flex:1;height:5px;background:rgba(15,23,42,.08);border-radius:3px;}}
.bf{{height:100%;border-radius:3px;}}

::-webkit-scrollbar{{width:5px;}}
::-webkit-scrollbar-thumb{{background:rgba(124,58,237,.3);border-radius:3px;}}
</style>
</head>
<body>

{page_html}

<script>
const D = {{
  monthly:  {monthly_j},
  category: {category_j},
  country:  {country_j},
  hourly:   {hourly_j},
  topCh:    {top_ch_j},
  dow:      {dow_j},
  models:   {model_j},
  pred:     {pred_j},
  res:      {res_j},
  stats:{{
    rec:{total_records}, vid:{unique_videos}, ch:{unique_channels},
    eng:{avg_engagement:.4f},
    bm:"{best_model['model']}",
    br2:{best_model['r2']:.4f},
    brmse:{best_model['rmse']:.4f}
  }}
}};

// CHART DEFAULTS
Chart.defaults.color = '#475569';
Chart.defaults.borderColor = 'rgba(15,23,42,0.08)';

function mkBar(id, labels, data, opts={{}}) {{
  const c = document.getElementById(id);
  if(!c) return;
  new Chart(c, {{
    type:'bar',
    data:{{labels, datasets:[{{data, borderRadius:6, borderSkipped:false, ...opts.ds}}]}},
    options:{{responsive:true,maintainAspectRatio:true,
      plugins:{{legend:{{display:false}}}},
      scales:{{
        x:{{grid:{{color:'rgba(15,23,42,0.06)'}}, ...opts.sx}},
        y:{{grid:{{color:'rgba(15,23,42,0.06)'}}, ...opts.sy}}
      }}, ...opts.extra}}
  }});
}}

// PAGE 1 — TỔNG QUAN
mkBar('cMonthly',
  D.monthly.map(d=>d.period),
  D.monthly.map(d=>d.count),
  {{ds:{{backgroundColor: D.monthly.map((_,i)=>`hsla(${{180+i*18}},75%,55%,.85)`)}}}}
);

if(document.getElementById('cHourly')) new Chart(document.getElementById('cHourly'),{{
  type:'line',
  data:{{
    labels: D.hourly.map(d=>d.publish_hour+'h'),
    datasets:[{{
      data: D.hourly.map(d=>+d.eng.toFixed(2)),
      borderColor:'#7c3aed', backgroundColor:'rgba(124,58,237,.12)',
      fill:true, tension:.4, pointRadius:4, pointBackgroundColor:'#7c3aed'
    }}]
  }},
  options:{{responsive:true,maintainAspectRatio:true,
    plugins:{{legend:{{display:false}}}},
    scales:{{
      x:{{grid:{{display:false}}}},
      y:{{grid:{{color:'rgba(15,23,42,0.06)'}}}}
    }}
  }}
}});

// Engagement theo thứ trong tuần — highlight "ngày vàng"
const dowVals = D.dow.map(d=>+d.eng.toFixed(2));
const bestDowIdx = dowVals.indexOf(Math.max(...dowVals));
mkBar('cDow',
  D.dow.map(d=>d.label),
  dowVals,
  {{ds:{{backgroundColor: D.dow.map((_,i)=> i===bestDowIdx ? 'rgba(5,150,105,.85)' : 'rgba(124,58,237,.55)')}}}}
);

const cx = ['#7c3aed','#06b6d4','#10b981','#f59e0b','#f43f5e','#8b5cf6','#0ea5e9','#14b8a6'];
const mxE = Math.max(...D.topCh.map(d=>d.engagement_rate));
if(document.getElementById('topCh')) document.getElementById('topCh').innerHTML = D.topCh
  .sort((a,b)=>b.engagement_rate-a.engagement_rate)
  .map((d,i)=>`
    <div style="margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;font-size:.79rem;margin-bottom:3px">
        <span style="color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:180px">${{d.channel_title}}</span>
        <span style="color:${{cx[i]}};font-weight:700">${{d.engagement_rate.toFixed(1)}}</span>
      </div>
      <div class="bb"><div class="bf" style="width:${{(d.engagement_rate/mxE*100).toFixed(1)}}%;background:${{cx[i]}}"></div></div>
    </div>`).join('');

// approx histogram from data distribution
const engBins = new Array(30).fill(0);
D.res.forEach(r=>{{ const b=Math.max(0,Math.min(29,Math.round(r+14))); engBins[b]++; }});
mkBar('cEngDist',
  engBins.map((_,i)=>i-14),
  engBins,
  {{ds:{{backgroundColor:'rgba(6,182,212,.65)'}}}}
);

// PAGE 2 — DANH MỤC & QUỐC GIA
const cc = D.category.map((_,i)=>`hsl(${{150+i*13}},65%,${{52+i%4*4}}%)`);
if(document.getElementById('cCat')) new Chart(document.getElementById('cCat'),{{
  type:'bar',
  data:{{
    labels: D.category.map(d=>d.category_name),
    datasets:[{{data:D.category.map(d=>+d.avg_engagement_rate.toFixed(3)),
      backgroundColor:cc, borderRadius:5, borderSkipped:false}}]
  }},
  options:{{responsive:true,maintainAspectRatio:false,
    indexAxis:'y',
    plugins:{{legend:{{display:false}}}},
    scales:{{
      x:{{grid:{{color:'rgba(15,23,42,0.06)'}}}},
      y:{{grid:{{display:false}},ticks:{{font:{{size:10}}}}}}
    }}
  }}
}});

const mxC = D.category.length > 0 ? Math.max(...D.category.map(d=>d.avg_engagement_rate)) : 1;
if(document.getElementById('tCat')) document.getElementById('tCat').innerHTML = `
<thead><tr><th>Danh mục</th><th>Eng. TB</th><th>Video</th></tr></thead>
<tbody>`+D.category.map((d,i)=>`
<tr>
  <td><span style="color:${{cc[i]}};font-size:.65rem">●</span> ${{d.category_name}}</td>
  <td>
    <div class="bw">
      <div class="bb" style="width:70px"><div class="bf" style="width:${{(d.avg_engagement_rate/mxC*100).toFixed(0)}}%;background:${{cc[i]}}"></div></div>
      <span>${{d.avg_engagement_rate.toFixed(2)}}</span>
    </div>
  </td>
  <td>${{(d.unique_videos||d.trending_records||0).toLocaleString()}}</td>
</tr>`).join('')+'</tbody>';

const crc = D.country.map((_,i)=>`hsl(${{340+i*22}},68%,${{52+i*2}}%)`);
mkBar('cCou',
  D.country.map(d=>d.country_code),
  D.country.map(d=>+d.avg_engagement_rate.toFixed(3)),
  {{ds:{{backgroundColor:crc}}}}
);

if(document.getElementById('cCouPie')) new Chart(document.getElementById('cCouPie'),{{
  type:'doughnut',
  data:{{
    labels: D.country.map(d=>d.country_code),
    datasets:[{{
      data: D.country.map(d=>d.trending_records),
      backgroundColor: D.country.map((_,i)=>`hsla(${{i*36}},68%,58%,.85)`),
      borderColor:'#ffffff', borderWidth:2
    }}]
  }},
  options:{{responsive:true,maintainAspectRatio:true,
    plugins:{{legend:{{display:true,position:'right',
      labels:{{font:{{size:11}},color:'#475569'}}}}}}
  }}
}});

// PAGE 3 — KẾT QUẢ ML
const mc = D.models.map(d=>d.r2>0?'rgba(124,58,237,.8)':'rgba(244,63,94,.7)');
if(document.getElementById('cR2')) new Chart(document.getElementById('cR2'),{{
  type:'bar',
  data:{{
    labels: D.models.map(d=>d.model),
    datasets:[{{data:D.models.map(d=>+d.r2.toFixed(4)),
      backgroundColor:mc, borderRadius:5, borderSkipped:false}}]
  }},
  options:{{responsive:true,maintainAspectRatio:true,indexAxis:'y',
    plugins:{{legend:{{display:false}}}},
    scales:{{x:{{min:-0.3,grid:{{color:'rgba(15,23,42,0.06)'}}}},y:{{grid:{{display:false}}}}}}
  }}
}});

if(document.getElementById('cRMSE')) new Chart(document.getElementById('cRMSE'),{{
  type:'bar',
  data:{{
    labels: D.models.map(d=>d.model),
    datasets:[{{data:D.models.map(d=>+d.rmse.toFixed(4)),
      backgroundColor:D.models.map(d=>d.rmse<3?'rgba(16,185,129,.8)':'rgba(244,63,94,.7)'),
      borderRadius:5, borderSkipped:false}}]
  }},
  options:{{responsive:true,maintainAspectRatio:true,indexAxis:'y',
    plugins:{{legend:{{display:false}}}},
    scales:{{x:{{grid:{{color:'rgba(15,23,42,0.06)'}}}},y:{{grid:{{display:false}}}}}}
  }}
}});

if(document.getElementById('cScatter')) new Chart(document.getElementById('cScatter'),{{
  type:'scatter',
  data:{{datasets:[
    {{data:D.pred.map(d=>({{x:+d.actual_engagement.toFixed(2),y:+d.predicted_engagement.toFixed(2)}})),
      backgroundColor:'rgba(124,58,237,.3)',pointRadius:3}},
    {{data:[{{x:0,y:0}},{{x:25,y:25}}],type:'line',
      borderColor:'rgba(244,63,94,.6)',borderDash:[5,5],pointRadius:0,borderWidth:1.5}}
  ]}},
  options:{{responsive:true,maintainAspectRatio:true,
    plugins:{{legend:{{display:false}}}},
    scales:{{
      x:{{title:{{display:true,text:'Actual'}},grid:{{color:'rgba(15,23,42,0.06)'}}}},
      y:{{title:{{display:true,text:'Predicted'}},grid:{{color:'rgba(15,23,42,0.06)'}}}}
    }}
  }}
}});

const rb={{}};
D.res.forEach(r=>{{const b=Math.round(r);rb[b]=(rb[b]||0)+1;}});
const rs=Object.keys(rb).sort((a,b)=>+a-+b);
if(document.getElementById('cRes')) new Chart(document.getElementById('cRes'),{{
  type:'bar',
  data:{{
    labels:rs,
    datasets:[{{data:rs.map(k=>rb[k]),
      backgroundColor:rs.map(k=>+k<0?'rgba(244,63,94,.6)':'rgba(124,58,237,.6)'),
      borderRadius:3,borderSkipped:false}}]
  }},
  options:{{responsive:true,maintainAspectRatio:true,
    plugins:{{legend:{{display:false}}}},
    scales:{{x:{{grid:{{display:false}}}},y:{{grid:{{color:'rgba(15,23,42,0.06)'}}}}}}
  }}
}});

if(document.getElementById('tMod')) document.getElementById('tMod').innerHTML=`
<thead><tr><th>#</th><th>Model</th><th>R2</th><th>RMSE</th><th>MAE</th><th>R2 log</th><th>RMSE log</th></tr></thead>
<tbody>`+D.models.map((d,i)=>`
<tr>
  <td style="color:var(--ts)">${{i+1}}</td>
  <td style="font-weight:600">${{d.model}}</td>
  <td><span class="bge ${{d.r2>0?'bg-g':'bg-r'}}">${{d.r2.toFixed(4)}}</span></td>
  <td>${{d.rmse.toFixed(4)}}</td>
  <td>${{d.mae.toFixed(4)}}</td>
  <td><span class="bge bg-b">${{d.r2_log.toFixed(4)}}</span></td>
  <td>${{d.rmse_log.toFixed(4)}}</td>
</tr>`).join('')+'</tbody>';
</script>
</body></html>"""
    return html