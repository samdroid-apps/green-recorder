install_data(['green-recorder.png'], install_dir : 'pixmaps')
install_data(['green-recorder.desktop'], install_dir : 'applications')

gnome = import('gnome')
gresource_bundle = gnome.compile_resources(
    'today.sam.green-recorder',
    'green-recorder.gresource.xml',
    gresource_bundle: true,
    install : true,
    install_dir : app_data_dir)
