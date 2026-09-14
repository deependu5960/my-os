.PHONY: iso clean

iso:
	@echo "ISO builds are handled by GitHub Actions."
	@echo "Push to main or manually run the Build OUR OS ISO workflow."

clean:
	rm -rf .build chroot cache binary config/bootstrap config/chroot config/common config/binary