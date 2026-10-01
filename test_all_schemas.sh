set -e

BASE_PATH="$(dirname "$0")/schema/tests"

python3 "$BASE_PATH/test_fff_material_default_properties.py"
python3 "$BASE_PATH/test_opt_db_schema.py"
