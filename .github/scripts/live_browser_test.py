"""Browser smoke test of the LIVE Render deployment using Chromium + Playwright."""
import re
from playwright.sync_api import sync_playwright

WEB = "https://indusim-3d-web.onrender.com"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage","--enable-unsafe-swiftshader",
                  "--use-gl=angle","--use-angle=swiftshader"])
        page = browser.new_page(viewport={"width":1440,"height":900}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)+"\\n"+str(e.stack)))
        response=page.goto(WEB,wait_until="domcontentloaded",timeout=90000)
        assert response and response.status==200
        page.get_by_role("heading",name="Datos de la planta").wait_for(timeout=90000)
        print("PASS: React landing configuration",flush=True)

        page.get_by_role("button",name=re.compile("Evaluar SLP")).click(timeout=20000)
        page.get_by_text("Evaluación del layout",exact=True).wait_for(timeout=90000)
        page.locator("canvas").first.wait_for(timeout=30000)
        page.screenshot(path="indusim_live_3d.png")
        print("PASS: SLP 3D canvas and layout inspector",flush=True)

        page.get_by_role("button",name=re.compile("Ejecutar simulación")).click(timeout=20000)
        page.get_by_text("Reproducción",exact=True).wait_for(timeout=90000)
        print("PASS: live simulation controls",flush=True)

        page.get_by_role("button",name=re.compile("APP · MPS · MRP")).click(timeout=20000)
        page.get_by_role("heading",name="APP · MPS · MRP").wait_for(timeout=30000)
        page.get_by_role("button",name=re.compile("Optimizar Planificación Agregada")).click()
        page.get_by_text("Costo mínimo APP del escenario",exact=True).wait_for(timeout=90000)
        print("PASS: APP optimization in browser",flush=True)

        page.get_by_role("button",name="Comparar seis políticas de planificación").click()
        page.get_by_role("columnheader",name="Política").wait_for(timeout=90000)
        page.screenshot(path="indusim_live_planning.png")
        print("PASS: APP policies comparison",flush=True)
        assert not errors, "Uncaught JavaScript errors: "+repr(errors)
        browser.close()
        print("ALL BROWSER TESTS PASSED",flush=True)

if __name__=="__main__":run()
