#!/bin/bash -eu

function init_rally {
    echo ">>> Create rally db..."
    if rally-manage db create; then
        echo ">>> Rally db created"
    else
        echo ">>> Database exists, upgrade schema"
        rally-manage db uograde
        echo ">>> Database upgraded"
    fi
}

function create_tempest_deployment {
    echo ">>> Create rally deployment..."
    rally deployment create --fromenv --name=tempest
    echo ">>> Deployment created"

    echo ">>> Install tempest..."
    rally verify install
    echo ">>> Tempest installed"
}

function generate_tempest_config {
    echo ">>> Generate tempest config..."
    local conf_path=$(mktemp)
    cat tempest/tempest.conf >> $conf_path
    cat <<EOF >> $conf_path
[network]
floating_network_name = ext-net
public_network_id = $(openstack network show ext-net -f value -c id)
EOF
    rally verify genconfig --add-options $conf_path
    rm $conf_path
    echo ">>> Tempest config:"
    rally verify showconfig
}

function run_tempest {
    echo ">>> Run tempest..."
    rc=0
    rally verify start --skip-list tempest/newton-skip-list.list || rc=$?
    echo ">>> Verify exited with code $rc"

    echo ">>> Generate report..."
    local output_file="tempest-report-$(date '+%Y-%m-%d__%H-%M-%S').html"
    rally verify results --html --output-file $output_file
    echo ">>> Report saved in: $output_file"
}

init_rally
create_tempest_deployment
generate_tempest_config
run_tempest

exit $rc
