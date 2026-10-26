import { useState } from 'react';
import BasicButton from '../../components/commons/BasicButton/BasicButton';
import BasicButtonTemplate from '../../components/playground/BasicButtonTemplate/BasicButtonTemplate';
import ContainerTemplate from '../../components/playground/ContainerTemplate/ContainerTemplate';
import FileTemplate from '../../components/playground/FileTemplate/FileTemplate';
import MessageTemplate from '../../components/playground/MessageTemplate/MessageTemplate';
import ModalTemplate from '../../components/playground/ModalTemplate/ModalTemplate';
import TextTemplate from '../../components/playground/TextTemplate/TextTemplate';
import { Link } from 'react-router-dom';
import LongTextTemplate from '../../components/playground/LongTextTemplate/LongTextTemplate';
import TagInputTemplate from '../../components/playground/TagInputTemplate/TagInputTemplate';

function PlayGroundPage() {

  const [currentTemplate, setCurrentTemplate] = useState('');

  const renderComponent = () => {
    switch(currentTemplate) {
      case 'basicButton':
        return <BasicButtonTemplate />;
      case 'container':
        return <ContainerTemplate />;
      case 'file':
        return <FileTemplate />;
      case 'message':
        return <MessageTemplate />
      case 'modal':
        return <ModalTemplate />;
      case 'text':
        return <TextTemplate />;
      case 'longText':
        return <LongTextTemplate />;
      case 'tagInput':
        return <TagInputTemplate />;
      default:
        return <div>Not Found</div>;
    }
  }

  return (
    <div>
      <div>
        <BasicButton type="button" value="api" onclickAction={() => setCurrentTemplate('api')}>api</BasicButton>
        <BasicButton type="button" value="basicButton" onclickAction={() => setCurrentTemplate('basicButton')}>basicButton</BasicButton>
        <BasicButton type="button" value="container" onclickAction={() => setCurrentTemplate('container')}>container</BasicButton>
        <BasicButton type="button" value="file" onclickAction={() => setCurrentTemplate('file')}>file</BasicButton>
        <BasicButton type="button" value="message" onclickAction={() => setCurrentTemplate('message')}>message</BasicButton>
        <BasicButton type="button" value="modal" onclickAction={() => setCurrentTemplate('modal')}>modal</BasicButton>
        <BasicButton type="button" value="text" onclickAction={() => setCurrentTemplate('text')}>text</BasicButton>
        <BasicButton type="button" value="longText" onclickAction={() => setCurrentTemplate('longText')}>long text</BasicButton>
        <BasicButton type="button" value="tagInput" onclickAction={() => setCurrentTemplate('tagInput')}>tag input</BasicButton>
        <div><Link to="/signin">サインインはこちら</Link></div>
      </div>
      <div>
        {renderComponent()}
      </div>
    </div>
  );
}

export default PlayGroundPage;
