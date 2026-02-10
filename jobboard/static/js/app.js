(function(){
  // theme toggle
  const key="jobboard_theme";
  const root=document.documentElement;
  const btn=document.getElementById("themeToggle");
  function setTheme(t){
    root.setAttribute("data-bs-theme", t);
    localStorage.setItem(key,t);
    if(btn) btn.setAttribute("aria-label", t==="dark" ? "Switch to light mode" : "Switch to dark mode");
  }
  const saved=localStorage.getItem(key);
  if(saved){ setTheme(saved); }

  if(btn){
    btn.addEventListener("click", function(){
      const cur=root.getAttribute("data-bs-theme") || "light";
      setTheme(cur==="dark" ? "light" : "dark");
    });
  }

  // Auto RTL if page contains a lot of Persian/Arabic chars and user hasn't set a preference
  try{
    const curDir=document.documentElement.getAttribute("dir");
    if(!curDir){
      const txt=document.body.innerText || "";
      const m=(txt.match(/[\u0600-\u06FF]/g)||[]).length;
      if(m>30){ document.documentElement.setAttribute("dir","rtl"); }
      else{ document.documentElement.setAttribute("dir","ltr"); }
    }
  }catch(e){}
})();
