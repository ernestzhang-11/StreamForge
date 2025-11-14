.PHONY: help verify-provider xhs-submodule-add xhs-submodule-update xhs-submodule-pin xhs-submodule-status

help:
	@echo "XHS upstream helpers:"
	@echo "  make verify-provider            # Show which XHS_Apis provider is used"
	@echo "  make xhs-submodule-add         # Add upstream repo as git submodule under vendor/Spider_XHS"
	@echo "  make xhs-submodule-update      # Update submodule to latest remote"
	@echo "  make xhs-submodule-pin REF=... # Pin submodule to a tag/commit"
	@echo "  make xhs-submodule-status      # Show submodule status"

verify-provider:
	python3 scripts/verify_xhs_provider.py

xhs-submodule-add:
	bash scripts/xhs_upstream.sh init-submodule

xhs-submodule-update:
	bash scripts/xhs_upstream.sh update-submodule

xhs-submodule-pin:
	bash scripts/xhs_upstream.sh pin-submodule "$(REF)"

xhs-submodule-status:
	bash scripts/xhs_upstream.sh status-submodule

