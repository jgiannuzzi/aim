import * as React from 'react';

import { Checkbox } from 'components/kit_v2';

function CheckboxVizElement(
  props: any,
): React.FunctionComponentElement<React.ReactNode> {
  const [checked, setChecked] = React.useState(props.data);

  React.useEffect(() => {
    if (props.data !== checked) {
      setChecked(props.data);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.data]);

  const onChange = React.useCallback((checked) => {
    setChecked(checked);
    props.callbacks?.on_change(checked);
  }, []);

  return (
    <Checkbox {...props.options} checked={checked} onCheckedChange={onChange} />
  );
}

CheckboxVizElement.displayName = 'CheckboxVizElement';
export default CheckboxVizElement;
