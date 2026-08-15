from app.api.v1.routes import router
from app.api.v1.vault_routes import vault_router
from app.api.v1.demo_routes import demo_router

router.include_router(vault_router)
router.include_router(demo_router)
