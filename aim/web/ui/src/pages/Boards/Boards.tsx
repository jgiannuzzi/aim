import React from 'react';

import { IconPlus } from '@tabler/icons-react';

import BusyLoaderWrapper from 'components/BusyLoaderWrapper/BusyLoaderWrapper';
import ErrorBoundary from 'components/ErrorBoundary/ErrorBoundary';
import NotificationContainer from 'components/NotificationContainer/NotificationContainer';
import { Box, Button, Input, Link, Text } from 'components/kit_v2';

import { PathEnum } from 'config/enums/routesEnum';
import { TopBar } from 'config/stitches/foundations/layout';

import { BoardsContainer, BoardsCardWrapper } from './Boards.style';
import BoardCard from './components/BoardCard/BoardCard';
import useBoards from './useBoards';

function Boards(): React.FunctionComponentElement<React.ReactNode> {
  const {
    data,
    filteredBoards,
    isLoading,
    notifyData,
    searchValue,
    onBoardDelete,
    handleSearchChange,
    onNotificationDelete,
  } = useBoards();

  return (
    <ErrorBoundary>
      <TopBar>
        <Text weight='$3'>BOARDS</Text>
      </TopBar>
      <BoardsContainer>
        <Box display='flex' ai='center'>
          <Box flex={1}>
            <Input
              inputSize='lg'
              value={searchValue}
              onChange={handleSearchChange}
              css={{ width: 380 }}
              placeholder='Search'
            />
          </Box>
          <Link
            underline={false}
            to={PathEnum.Board.replace(':boardId', 'new')}
          >
            <Button
              size='lg'
              leftIcon={<IconPlus color='white' />}
              color='success'
            >
              New
            </Button>
          </Link>
        </Box>
        <BusyLoaderWrapper isLoading={isLoading} height={'100%'}>
          <BoardsCardWrapper>
            {data?.length > 0 &&
              filteredBoards.map((board: any) => (
                <BoardCard
                  key={board.id}
                  onBoardDelete={onBoardDelete}
                  {...board}
                />
              ))}
          </BoardsCardWrapper>
        </BusyLoaderWrapper>
      </BoardsContainer>
      {notifyData?.length > 0 && (
        <NotificationContainer
          handleClose={onNotificationDelete}
          data={notifyData}
        />
      )}
    </ErrorBoundary>
  );
}

export default Boards;
