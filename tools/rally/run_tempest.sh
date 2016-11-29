#!/bin/bash -eu

set -o pipefail

function init_rally {
    echo ">>> Create rally db..."
    if rally-manage db create; then
        echo ">>> Rally db created"
    else
        echo ">>> Database exists, upgrade schema"
        rally-manage db upgrade
        echo ">>> Database upgraded"
    fi
}

function create_tempest_deployment {
    echo ">>> Create rally deployment..."
    if rally deployment create --fromenv --name=tempest; then
        echo ">>> Deployment created"
    else
        echo ">>> Using existing deployment"
    fi

    echo ">>> Install tempest..."
    rally verify install
}

function generate_tempest_config {
    echo ">>> Generate tempest config..."
    local conf_path="$(mktemp)"
    cat "$WORKDIR/tempest/tempest.conf" >> "$conf_path"
    cat <<EOF >> "$conf_path"
[network]
floating_network_name = ext-net
public_network_id = $(openstack network show ext-net -f value -c id)
EOF
    rally verify genconfig --add-options "$conf_path"
    rm "$conf_path"
    echo ">>> Tempest config:"
    rally verify showconfig
}

function run_tempest {
    echo ">>> Run tempest..."
    rally verify start --skip-list "$WORKDIR/tempest/newton-skip-list.list"

}

function check_result {
    echo ">>> Generate report..."
    local output_file="$WORKDIR/tempest-report-$(date '+%Y-%m-%d__%H-%M-%S').html"
    rally verify results --html --output-file "$output_file"
    echo ">>> Report saved in: $output_file"
    rally verify results | "$WORKDIR/tools/rally/check_status.py"
}

init_rally
create_tempest_deployment
generate_tempest_config
run_tempest
check_result
